import copy
import logging
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Collection, Generator, Iterable, List, Literal, Optional, Set

from autopcb.layout.delaunator import delaunay
from autopcb.datatypes.common import BoundingBox, Vector2DWithRotation, Vector2D
from autopcb.datatypes.pcb import Board, Footprint, Pad
from autopcb.datatypes.mixins import DataclassSerializerMixin

logger = logging.getLogger(__name__)

@dataclass
class Line:
    """Line that serves as a value for each rats nest element"""

    x1: float
    x2: float
    y1: float
    y2: float


NetList = dict[str, List[Vector2D]]
# A dict {"net name": list of points (pad positions) in the net}
# not all NetLists should be a default dict,
# for example when one is returned from a get_netlist function,
# it should no longer have the default factory. So creating a separate type
# for a general netlist, and one with a default dict can be used with
# net_list: NetList = defaultdict(list)


RatsNest = dict[str, List[Line]]
# Represents a KiCAD rats nest

class PlacementStatusType(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INITIALIZED = "initialized"


class PlacementIssueType(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(kw_only=True)
class PlacementIssue:
    type: PlacementIssueType
    message: str | None = field(default=None)

    def _eq__(self, other):
        return self.type == other.type and self.message == other.message


@dataclass(kw_only=True)
class PlacementStatus(DataclassSerializerMixin):
    """Stores information about the autoplacement status
    and a list of important past statuses like warnings and errors"""

    status: PlacementStatusType = field(default=PlacementStatusType.INITIALIZED)
    issues: List[PlacementIssue] = field(default_factory=list)

    def log_issue(self, issue_type: PlacementIssueType, message: Optional[str] = None) -> None:
        """Logs an issue encountered during autoplacement and sets a global status"""
        issue = PlacementIssue(type=issue_type, message=message)
        # Check for duplicate issues
        if issue in self.issues:
            return

        # If a fatal issue was encountered, indicate placement failure
        self.issues.append(issue)
        if issue_type == PlacementIssueType.ERROR:
            self.status = PlacementStatusType.FAILED


@dataclass(kw_only=True)
class IntermediateState(DataclassSerializerMixin):
    """Returned by next(ComponentAutoplacer.component_placement_generator) generator to yield
    an intermittent state to update the gui"""

    current_footprint_bounding_box: BoundingBox | None = field(default=None)
    placed_footprints_bounding_boxes: List[BoundingBox] = field(default_factory=list)
    previously_tested_footprint_positions_for_rendering: List[Vector2DWithRotation] = field(default_factory=list)
    current_footprint_ratsnest: RatsNest = field(default_factory=RatsNest)
    full_ratsnest: RatsNest = field(default_factory=RatsNest)
    components_overlap: bool = field(default=False)


@dataclass
class ComponentAutoplacer(DataclassSerializerMixin):
    """A class for operations regarding PCB footprint placement optimization"""

    board: Board
    placed_components: Set[Footprint]
    footprints_not_placed_yet: List[Footprint]
    rotation_settings: List[int]
    board_outline: BoundingBox | None
    intermediate_state: IntermediateState | None
    placement_status: PlacementStatus

    def __init__(self, board: Board, board_outline: BoundingBox | None = None):
        self.board: Board = board
        self.board_outline = board_outline
        self.placed_components: Set[Footprint] = set()
        self.placement_status: PlacementStatus = PlacementStatus()
        # move all footprints far away
        for footprint in self.board.footprints:
            if not footprint.locked:
                footprint.set_position(Vector2DWithRotation(100, 100, 0))
        # _prepare_placement_waitlist() will set the position of the first element
        self.footprints_not_placed_yet: Set[Footprint] = self._prepare_placement_waitlist()
        self.intermediate_state: IntermediateState | None = IntermediateState()
        self.rotation_settings: List[int] = [0, 90, 180, 270]
        self.full_rats_nest: RatsNest = get_rats_nest(self.board.footprints, nets_to_skip=['GND'])

    def _prepare_placement_waitlist(self) -> Set[Footprint]:
        """Prepares the placement waitlist by excluding correctly placed locked components"""
        footprints = set(self.board.footprints)
        for component in self.board.locked_components:
            component.placed = True
            self.placed_components.add(component)
            footprints.discard(component)

            if self.board_outline is not None and not self.board_outline.contains(component._bounding_box):
                self.placement_status.log_issue(
                    PlacementIssueType.ERROR, "Some locked components are positioned outside of selected outline."
                )
            if check_global_footprint_overlap(
                component, self.board.locked_components.difference({component}), margin=0
            ):
                self.placement_status.log_issue(
                    PlacementIssueType.WARNING, "Two or more locked components overlap each other."
                )
        return footprints

    def place_footprint(self, footprint: Footprint, position: Vector2DWithRotation):
        """Places the footprint and updates the board information"""
        footprint.set_position(position)
        footprint.placed = True
        self.board.replace_footprint(footprint)
        self.placed_components.add(footprint)
        self.footprints_not_placed_yet.discard(footprint)

    def component_placement_generator(
        self, margin, debug_level: Literal[0] | Literal[1] | Literal[2] | Literal[3] | Literal[4] = 0
    ) -> Generator[IntermediateState | None, Any, None]:
        """Generator for components placement. The general strategy is performing
        a breadth first search starting with either the most connected footprint or locked footprints"""
        if len(self.placed_components) == 0:  # if no footprints are locked, none have been placed yet
            # so start with placing the most connected footprint at the center of the PCB
            first_footprint = get_the_most_connected_footprint(self.footprints_not_placed_yet)
            self.place_footprint(first_footprint, Vector2DWithRotation(0, 0, 0))
        while len(self.footprints_not_placed_yet) > 0 and self.placement_status.status != PlacementStatusType.FAILED:
            """Places the next footprint in the board, and yield the board object with the updated positions"""
            # todo fixme: also skip the power plane net
            self.placement_status.status = PlacementStatusType.RUNNING
            placement_batch = set()
            for footprint in self.placed_components:
                # Create a placement batch composed of all footprints connected to already placed ones
                # Equivalent to performing a breadth first search starting with either:
                # the most connected footprint, or locked footprints
                directly_connected = footprint.get_directly_connected_footprints(self.board.footprints)
                new_footprints_to_place = directly_connected - self.placed_components
                self.footprints_not_placed_yet -= new_footprints_to_place
                placement_batch |= new_footprints_to_place

            if not placement_batch:
                try:
                    # Add the next component from waitlist to placement batch
                    next_footprint = self.footprints_not_placed_yet.pop()
                    # Only display warning if isolated footprint is not a mounting hole
                    if not next_footprint.name.startswith("MountingHole"):
                        self.placement_status.log_issue(
                            PlacementIssueType.WARNING, "The circuit has electrically isolated components."
                        )
                    placement_batch.add(next_footprint)
                except IndexError:
                    # Waitlist is empty, terminate placement
                    self.placement_status.status = PlacementStatusType.SUCCESS
                    break

            for placement_candidate in placement_batch:
                if self.placed_components & self.footprints_not_placed_yet != set():
                    raise Exception(
                        'This should not have happened! a '
                        'component is in both self.placed_components & self.footprints_not_placed_yet'
                    )
                # only used to display historically tested dots on the frontend for debugging the algorithm itself
                previously_tested_footprint_positions_for_rendering = []

                best_position: Vector2DWithRotation | None = None
                best_distance: float = float("inf")
                search_center = self.get_search_center(placement_candidate)

                max_radius = 1000
                dx = 1
                for radius in range(0, max_radius, dx):
                    # if we still haven't found a suitable position
                    if best_position is None and self.board_outline is not None:
                        # and the area we're searching is fully outside the valid board outline
                        if radius > self.board_outline.width and radius > self.board_outline.height:
                            self.placement_status.log_issue(
                                PlacementIssueType.ERROR, "Selected board outline is to find a space for this footprint"
                            )
                            break

                    # in this block of code, the word "overlap" means
                    # the chip currently being placed has overlapped with one of the already placed chips
                    is_there_an_overlap_in_this_circle = False
                    for point in points_on_circle(search_center, radius, dx):
                        for rotation in self.rotation_settings: 
                            candidate_position = Vector2DWithRotation(point.x, point.y, rotation)
                            previously_tested_footprint_positions_for_rendering.append(candidate_position)
                            placement_candidate.set_position(candidate_position)
                            do_footprints_overlap = check_global_footprint_overlap(
                                placement_candidate, self.placed_components, margin
                            )
                            if do_footprints_overlap:
                                is_there_an_overlap_in_this_circle = True
                            is_footprint_in_board_outline = self.board_outline is None or self.board_outline.contains(
                                placement_candidate._bounding_box
                            )
                            current_footprint_ratsnest = get_connections_to_closest_other_footprints(
                                placement_candidate, self.placed_components
                            )
                            if "GND" in current_footprint_ratsnest:  # todo fixme: also skip the power plane net
                                del current_footprint_ratsnest[
                                    "GND"
                                ]  # don't include the GND net in the calculations or rendering
                            if debug_level >= 1:  # For debug_level = 0 only return the last yield
                                self.intermediate_state = IntermediateState(
                                    current_footprint_bounding_box=placement_candidate._bounding_box,
                                    placed_footprints_bounding_boxes=[
                                        footprint._bounding_box for footprint in self.placed_components
                                    ],
                                    current_footprint_ratsnest=current_footprint_ratsnest,
                                    full_ratsnest=self.full_rats_nest,
                                    previously_tested_footprint_positions_for_rendering=previously_tested_footprint_positions_for_rendering,
                                    components_overlap=do_footprints_overlap or not is_footprint_in_board_outline,
                                )
                                yield self.intermediate_state

                            distance: float = 0
                            for line_list in current_footprint_ratsnest.values():
                                for line in line_list:
                                    distance += manhattan_distance(line)

                            if distance < best_distance and not do_footprints_overlap and is_footprint_in_board_outline:
                                best_distance = distance
                                best_position = candidate_position
                    if best_distance != float('inf'):
                        break
                    # use the following as a more rigorous stopping condition
                    # if not is_there_an_overlap_in_this_circle:  # no need for further search
                    #     break  # once we complete a full circle at one radius without any overlaps
                # At this point, done searching through different positions
                # If best position could not be determined, set it to current position
                if best_position is None:
                    best_position = placement_candidate.at
                    # TODO FIXME @Jakub do we need to do anything else here for better handling?
                    self.placement_status.log_issue(PlacementIssueType.ERROR, "Could not place a component")
                self.place_footprint(placement_candidate, best_position)

        # Return a different flag on intermediateState
        # rather than raising StopIteration because an exception requires a lot more boilerplate to catch in pyodide
        if len(self.footprints_not_placed_yet) == 0 and self.placement_status.status != PlacementStatusType.SUCCESS:
            self.placement_status.status = PlacementStatusType.SUCCESS

        yield self.intermediate_state

    def place_all_components(self, margin):
        """Exhausts component placement generator and dumps placement status"""
        try:
            deque(self.component_placement_generator(margin))
        except StopIteration:
            pass

        return self.placement_status.dumps()

    def get_search_center(self, footprint: Footprint) -> Vector2D:
        """Given a footprint, find the mean position to all the other pads this footprint needs to be connected to"""
        other_pad_positions: list[Vector2D] = []
        for pad in footprint.pads:
            if pad.net is None:  # If the current pad isn't connected to a net, skip it
                continue
            for other_footprint in self.placed_components:
                if other_footprint is footprint:  # skip self
                    continue
                for other_pad in other_footprint.pads:
                    if other_pad.net is None:  # If other pad is not connected to a net, skip
                        continue
                    if other_pad.net.name != pad.net.name:  # If other pad is not connected to a different net, skip
                        continue
                    other_pad_positions.append(get_global_position(other_pad, other_footprint))
        if len(other_pad_positions) == 0:
            print('No best start position')
            return Vector2D(0, 0)
        mean_x = mean([point.x for point in other_pad_positions])
        mean_y = mean([point.y for point in other_pad_positions])
        return Vector2D(mean_x, mean_y)


def normalize_angle(angle):
    """Normalize any input angle (including negative) to be [0, 360)"""
    return angle % 360 if angle >= 0 else 360 + (angle % 360)


def mean(something: Collection):
    return sum(something) / len(something)


def get_net_list(footprints: Iterable[Footprint]) -> NetList:
    """Gets coordinates of pads for every net name

    Args:
        footprints (List[Footprint): a list of footprints to obtain pad positions from

    Returns:
        NetList: netlist of vertices for every net

    """
    net_list: NetList = defaultdict(list)
    for footprint in footprints:
        for pad in footprint.pads:
            if pad.net is not None:
                pad_x, pad_y = pad.at.x, pad.at.y
                parent_footprint_angle = normalize_angle(
                    footprint.at.rot if footprint.at.rot is not None else 0
                )
                if parent_footprint_angle % 90 != 0:
                    raise Exception('The footprint should only multiples of 90 degrees')
                number_of_rotations = round(parent_footprint_angle / 90)
                for _ in range(number_of_rotations):
                    pad_x, pad_y = pad_y, -pad_x
                net_list[pad.net.name].append(Vector2D(pad_x + footprint.at.x, pad_y + footprint.at.y))

    # Turn the default dict into a regular dict so it no longer automatically adds missing keys
    return NetList(net_list)


def get_connections_to_closest_other_footprints(
    footprint: Footprint, other_footprints: Set[Footprint]
) -> RatsNest:
    """Given a footprint, for each pad, find the line to the nearest pad on
    another footprint that is on the same net as the current footprint's pad.
    This is a good approximation for delaunay triangulation, but much faster"""
    part_rats_nest: RatsNest = defaultdict(list)
    for pad in footprint.pads:
        if pad.net is None:  # If the current pad isn't connected to a net, skip it
            continue
        current_pad_position = get_global_position(pad, footprint)
        best_distance_to_other_pad = float('inf')
        for other_footprint in other_footprints:
            for other_pad in other_footprint.pads:
                if other_pad.net is None:  # If other pad is not connected to a net, skip
                    continue
                if other_pad.net.name != pad.net.name:  # If other pad is not connected to a different net, skip
                    continue
                other_pad_position = get_global_position(other_pad, other_footprint)
                line_between_pads = line_from_two_points(other_pad_position, current_pad_position)
                distance = manhattan_distance(line_between_pads)
                if distance < best_distance_to_other_pad:
                    best_distance_to_other_pad = distance
                    part_rats_nest[pad.net.name].append(line_between_pads)

    # Turn the default dict into a regular dict so it no longer automatically adds missing keys
    return RatsNest(part_rats_nest)


def manhattan_distance(line: Line) -> float:
    """Use the manhattan distance rather than euclidian to penalize not being on a grid (and since we're using manhattan routing)"""
    return abs(line.x1 - line.x2) + abs(line.y1 - line.y2)


def line_from_two_points(point_a: Vector2D, point_b: Vector2D) -> Line:
    """Returns a line compose that passes through two vertices"""
    return Line(x1=point_a.x, y1=point_a.y, x2=point_b.x, y2=point_b.y)


def get_global_position(pad: Pad, footprint: Footprint) -> Vector2D:
    """Gets global footprint position"""
    other_pad_x, other_pad_y = pad.at.x, pad.at.y
    parent_footprint_angle = normalize_angle(footprint.at.rot if footprint.at.rot is not None else 0)
    if parent_footprint_angle % 90 != 0:
        raise Exception('The footprint should only multiples of 90 degrees')
    number_of_rotations = round(parent_footprint_angle / 90)
    for _ in range(number_of_rotations):
        other_pad_x, other_pad_y = other_pad_y, -other_pad_x
    return Vector2D(other_pad_x + footprint.at.x, other_pad_y + footprint.at.y)


def linspace(start: float, end: float, num: int):
    """Like numpy.linspace with two differences:
    - end is not *not* inclusive
    - written in pure python, so no numpy dependency (easier for pyodide)"""
    delta = end - start
    for i in range(num):
        yield start + i * delta / num


def points_on_circle(center: Vector2D, radius: int, dx: int) -> Generator[Vector2D, None, None]:
    point = copy.copy(center)  # don't interfere with the point given to us
    point.y -= radius
    point.x += radius
    yield point
    for _ in range(0, 2 * radius, dx):  # move down
        point.x -= dx
        yield point
    for _ in range(0, 2 * radius, dx):  # move left
        point.y += dx
        yield point
    for _ in range(0, 2 * radius, dx):  # move up
        point.x += dx
        yield point
    for _ in range(0, 2 * radius - dx, dx):  # move right
        # don't do the very last point since it's the same as the first point yielded in this generator
        point.y -= dx
        yield point


def get_rats_nest(footprints: Iterable[Footprint], nets_to_skip: Optional[list[str]] = None) -> RatsNest:
    """Gets the rats nest of input footprints.
    Skip nets with many connections for speed (such as GND or power plane)"""
    rats_nest: RatsNest = RatsNest()
    net_list: NetList = get_net_list(footprints)
    nets_to_skip = nets_to_skip or []

    for net_name, vertices in net_list.items():
        if net_name in nets_to_skip:
            # Skip nets with many connections for speed (such as GND or power plane which have 10x/100x more pins)
            continue
        if not vertices:
            raise AttributeError("Net has no vertices. That should not happen.")
        elif len(vertices) == 1:
            continue
        elif len(vertices) == 2:
            rats_nest[net_name] = [Line(x1=vertices[0].x, x2=vertices[1].x, y1=vertices[0].y, y2=vertices[1].y)]
            continue
        elif len(vertices) == 3:
            rats_nest[net_name] = [
                Line(x1=vertices[0].x, x2=vertices[1].x, y1=vertices[0].y, y2=vertices[1].y),
                Line(x1=vertices[1].x, x2=vertices[2].x, y1=vertices[1].y, y2=vertices[2].y),
                Line(x1=vertices[2].x, x2=vertices[0].x, y1=vertices[2].y, y2=vertices[1].y),
            ]
            continue

        edge_coordinates = []
        for triangle in delaunay(vertices):
            v1, v2, v3 = triangle.vertices
            edges = {
                ((v1.x, v1.y), (v2.x, v2.y)),
                ((v2.x, v2.y), (v3.x, v3.y)),
                ((v3.x, v3.y), (v1.x, v1.y)),
            }
            for (ax, ay), (bx, by) in edges:
                edge_coordinates.append(Line(x1=ax, x2=bx, y1=ay, y2=by))

        rats_nest[net_name] = edge_coordinates

    return rats_nest


def get_the_most_connected_footprint(footprints: Iterable[Footprint]) -> Footprint:
    most_connected_footprint = None
    most_connected_footprints_number_of_connections = 0
    for footprint in footprints:
        nets_this_footprint_is_connected_to = set([pad.net.name for pad in footprint.pads if pad.net is not None])
        nets_this_footprint_is_connected_to.discard('GND')  # TODO FIXME remove power nets as well
        if len(nets_this_footprint_is_connected_to) > most_connected_footprints_number_of_connections:
            most_connected_footprints_number_of_connections = len(nets_this_footprint_is_connected_to)
            most_connected_footprint = footprint
    if most_connected_footprint is None:
        most_connected_footprint = next(iter(footprints))  # don't crash if the user's board has no connections
        print('No connections in this board')  # todo fixme maybe send this to the frontend
    return most_connected_footprint


def check_global_footprint_overlap(
    footprint: Footprint,
    comparison_footprints: Iterable[Footprint],
    margin: float,
) -> bool:
    """Checks whether the footprint overlap any footprint in comparison array"""
    return any(footprint._bounding_box.overlaps(comparison._bounding_box, margin) for comparison in comparison_footprints)


def vertex_distance(v1: Vector2D, v2: Vector2D) -> float:
    """Gets Euclidean distance between two vertices"""
    return math.sqrt((v1.x - v2.x) ** 2 + (v1.y - v2.y) ** 2)