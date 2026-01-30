from dataclasses import dataclass
import math
from typing import Optional

from autopcb.datatypes.fields import positional
from autopcb.datatypes.mixins import DataclassSerializerMixin


@dataclass
class Margins:
    left: float = positional()
    top: float = positional()
    right: float = positional()
    bottom: float = positional()


@dataclass
class Vector2D:
    x: float = positional()
    y: float = positional()

    def __getitem__(self, item: int) -> float:
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError

    def __mul__(self, scalar: int | float):
        if isinstance(scalar, (int, float)):
            return Vector2D(self.x * scalar, self.y * scalar)
        raise NotImplementedError(f'Trying to multiply a vectory by a {type(scalar)}')

    def __rmul__(self, scalar: int | float):
        return self.__mul__(scalar)  # Delegate since scalar multiplication is commutative

    def __eq__(self, other: "Vector2D") -> bool:
        return self.x == other.x and self.y == other.y

    def __add__(self, other):
        if isinstance(other, Vector2D):
            return Vector2D(self.x + other.x, self.y + other.y)
        elif isinstance(other, int) or isinstance(other, float):
            return Vector2D(self.x + other, self.y + other)

    def __sub__(self, other):
        if isinstance(other, Vector2D):
            return Vector2D(self.x - other.x, self.y - other.y)
        elif isinstance(other, int) or isinstance(other, float):
            return Vector2D(self.x - other, self.y - other)

    def __truediv__(self, other):
        if isinstance(other, Vector2D):
            return Vector2D(self.x / other.x, self.y / other.y)
        elif isinstance(other, int) or isinstance(other, float):
            return Vector2D(self.x / other, self.y / other)

    def rotate(self, rotation_center: "Vector2D", angle: float):
        """Rotates the point around a second point"""
        rotation_angle = -math.radians(angle)
        s, c = math.sin(rotation_angle), math.cos(rotation_angle)
        self.x -= rotation_center.x
        self.y -= rotation_center.y
        x_new = self.x * c - self.y * s + rotation_center.x
        y_new = self.x * s + self.y * c + rotation_center.y
        self.x = x_new
        self.y = y_new

    def __abs__(self):
        return Vector2D(
            x=abs(self.x),
            y=abs(self.y),
        )

    @property
    def to_tuple(self) -> tuple:
        return tuple([self.x, self.y])

    def distance_to(self, other: "Vector2D") -> float:
        pythagorean_vertex = self - other
        square_distance = pythagorean_vertex.x**2 + pythagorean_vertex.y**2
        rooted_distance = math.sqrt(square_distance)
        return rooted_distance


@dataclass
class Vector2DWithRotation:
    x: float = positional()
    y: float = positional()
    rot: Optional[float] = positional()

    def __post_init__(self):
        if self.rot is None:
            self.rot = 0

    def __eq__(self, other: "Vector2DWithRotation") -> bool:
        return self.x == other.x and self.y == other.y and self.rot == other.rot

    def __add__(self, other: "Vector2DWithRotation"):
        return Vector2DWithRotation(self.x + other.x, self.y + other.y, self.rot + other.rot)

    def __sub__(self, other: "Vector2DWithRotation"):
        return Vector2DWithRotation(self.x - other.x, self.y - other.y, self.rot - other.rot)

    def __truediv__(self, other: int | float):
        return Vector2DWithRotation(self.x / other, self.y / other, self.rot)

    def rotate_about_origin(self, angle: float):
        """Rotate 90 counterclockwise about the origin"""
        if angle % 90 != 0:
            raise NotImplementedError('Rotations by angles not multiples of 90 degrees not implemented yet')
        normalized_angle = angle % 360 
        for i in range(int(normalized_angle / 90)):
            self.x, self.y = -self.y, self.x

    def rotate(self, rotation_center: "Vector2DWithRotation", angle: float):
        """Rotates the point around a second point"""
        rotation_angle = -math.radians(angle)
        s, c = math.sin(rotation_angle), math.cos(rotation_angle)
        self.x -= rotation_center.x
        self.y -= rotation_center.y
        x_new = self.x * c - self.y * s + rotation_center.x
        y_new = self.x * s + self.y * c + rotation_center.y
        self.x = x_new
        self.y = y_new
        self.rot = self.rot + angle


@dataclass
class BoundingBox(DataclassSerializerMixin):
    """Represents a bounding box.

    Attributes:
        x (float): The x-coordinate of the top-left corner.
        y (float): The y-coordinate of the top-left corner.
        width (float): The width of the bounding box.
        height (float): The height of the bounding box.
    """

    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> Vector2D:
        """Returns a vertex representing the center of the bounding box."""
        return Vector2D(self.x + self.width / 2, self.y + self.height / 2)

    @property
    def origin(self) -> Vector2D:
        """Returns the vertex representing top-left corner of the bounding box"""
        return Vector2D(self.x, self.y)

    def translate(self, x: float, y: float):
        """Translates the bounding box"""
        return BoundingBox(self.x + x, self.y + y, self.width, self.height)

    def rotate(self, rotation: float = 0, rotation_center: Vector2D | None = None):
        """Rotates the bounding box by an angle over its center or specified rotation point"""

        if rotation_center is not None:
            rotation_point = rotation_center
        else:
            center_x = self.x + self.width / 2
            center_y = self.y + self.height / 2
            rotation_point = Vector2D(center_x, center_y)

        corners = [
            Vector2D(self.x, self.y),
            Vector2D(self.x + self.width, self.y),
            Vector2D(self.x, self.y + self.height),
            Vector2D(self.x + self.width, self.y + self.height),
        ]

        for index, corner in enumerate(corners):
            corners[index].rotate(rotation_point, rotation)

        min_x = min(point.x for point in corners)
        min_y = min(point.y for point in corners)
        max_x = max(point.x for point in corners)
        max_y = max(point.y for point in corners)

        new_width = max_x - min_x
        new_height = max_y - min_y

        return BoundingBox(
            min_x,
            min_y,
            new_width,
            new_height,
        )

    def overlaps(self, other: 'BoundingBox', margin: float = 0) -> bool:
        bbox = BoundingBox(
            self.x - margin,
            self.y - margin,
            self.width + margin * 2,
            self.height + margin * 2,
        )
        return not (
            bbox.x + bbox.width <= other.x - margin
            or bbox.x >= other.x + other.width + margin
            or bbox.y + bbox.height <= other.y - margin
            or bbox.y >= other.y + other.height + margin
        )

    def contains(self, other: 'BoundingBox') -> bool:
        """Checks if this bounding box completely contains another bounding box."""
        return (
            self.x <= other.x
            and self.y <= other.y
            and self.x + self.width >= other.x + other.width
            and self.y + self.height >= other.y + other.height
        )

    def __add__(self, other: 'BoundingBox') -> 'BoundingBox':
        """Computes the aggregated bounding box that encompasses both bounding boxes."""
        min_x = min(self.x, other.x)
        min_y = min(self.y, other.y)
        max_x = max(self.x + self.width, other.x + other.width)
        max_y = max(self.y + self.height, other.y + other.height)
        
        return BoundingBox(
            min_x,
            min_y,
            max_x - min_x,
            max_y - min_y,
        )

    def __radd__(self, other):
        """Right-hand addition for sum() compatibility."""
        if other == 0:
            return self
        return self.__add__(other)

    def __eq__(self, other: 'BoundingBox') -> bool:
        # Use math.isclose because floating point errors accumulate somewhere
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y) and math.isclose(self.height, other.height) and math.isclose(self.width, other.width)



@dataclass
class StandardLine:
    """A line in a coordinate grid described in standard form (ax + by = c)"""
    x_quantifier: float
    y_quantifier: float
    equates: float

    def __str__(self) -> str:
        return f"{self.A}x + {self.B}y = {self.C}"

    @property
    def A(self) -> float:
        return self.x_quantifier

    @property
    def B(self) -> float:
        return self.y_quantifier

    @property
    def C(self) -> float:
        return self.equates

    def intersection(self, other: "StandardLine") -> Vector2D:
        determinant = self.A * other.B - other.A * self.B
        if determinant == 0:  # The lines are parallel
            raise ValueError(f"The lines {self} and {other} do not intersect.")
        else:
            return Vector2D(x=(other.B * self.C - self.B * other.C) / determinant, y=(self.A * other.C - other.A * self.C) / determinant)

    @staticmethod
    def from_points(p: Vector2D, q: Vector2D) -> "StandardLine":
        return StandardLine(x_quantifier=q.y - p.y, y_quantifier=p.x - q.x, equates=(q.y - p.y) * p.x + (p.x - q.x) * p.y)


@dataclass
class Coordinate:
    """A single x or y coordinate that doesn't have a specific value yet"""
    min: float
    max: float

    @property
    def diff(self) -> float:
        return self.max - self.min

    @property
    def center(self) -> float:
        return self.min + self.diff * 0.5


@dataclass
class Edge:
    """An Edge - a line(AB) in 2D space described by 2 vertices"""
    a: Vector2D
    b: Vector2D

    def __getitem__(self, item) -> Vector2D:
        if item == 0:
            return self.a
        elif item == 1:
            return self.b
        else:
            raise IndexError

    def __eq__(self, other) -> bool:
        if isinstance(other, Edge):
            if self.a == other.a and self.b == other.b:
                return True
            elif self.b == other.a and self.a == other.b:
                return True
            return False
        else:
            raise AssertionError(f"Cannot compare Edge to {other.__class__}")

    @property
    def vertices(self) -> list[Vector2D]:
        return [self.a, self.b]


@dataclass
class Triangle:
    """
    A Triangle represented as 3 vertices a, b, c
    """

    a: Vector2D
    b: Vector2D
    c: Vector2D
    is_super: bool = False

    def __getitem__(self, item) -> Vector2D:
        if item == 0:
            return self.a
        elif item == 1:
            return self.b
        elif item == 2:
            return self.c
        else:
            raise IndexError

    def __eq__(self, other) -> bool:
        if isinstance(other, Triangle):
            if self.a == other.a and self.b == other.b and self.c == other.c:
                return True
            return False
        else:
            raise AssertionError(f"Cannot compare Triangle to {other.__class__}")

    @property
    def ab_center(self) -> Vector2D:
        return (self.a + self.b) / 2

    @property
    def bc_center(self) -> Vector2D:
        return (self.b + self.c) / 2

    @property
    def ca_center(self) -> Vector2D:
        return (self.c + self.a) / 2

    @property
    def ab_edge(self) -> Edge:
        return Edge(a=self.a, b=self.b)

    @property
    def bc_edge(self) -> Edge:
        return Edge(a=self.b, b=self.c)

    @property
    def ca_edge(self) -> Edge:
        return Edge(a=self.c, b=self.a)

    @property
    def vertices(self) -> list[Vector2D]:
        return [self.a, self.b, self.c]

    @property
    def edges(self) -> list[Edge]:
        return [self.ab_edge, self.bc_edge, self.ca_edge]

    @property
    def circumcenter(self) -> Vector2D:
        ab = StandardLine.from_points(p=self.a, q=self.b)
        bc = StandardLine.from_points(p=self.b, q=self.c)

        pb_ab = StandardLine(x_quantifier=-ab.B, y_quantifier=ab.A, equates=-ab.B * ((self.a + self.b) / 2).x + ab.A * ((self.a + self.b) / 2).y)
        pb_bc = StandardLine(x_quantifier=-bc.B, y_quantifier=bc.A, equates=-bc.B * ((self.b + self.c) / 2).x + bc.A * ((self.b + self.c) / 2).y)

        return pb_ab.intersection(pb_bc)

    @property
    def circumradius(self) -> float:
        return self.circumcenter.distance_to(self.a)

    @property
    def circumcircle(self):
        return Circle(center=self.circumcenter, radius=self.circumradius)


@dataclass
class Circle:
    """A Circle described by its center and its radius"""

    center: Vector2D
    radius: float

    def encompasses_vertex(self, vertex: Vector2D) -> bool:
        if self.radius >= self.center.distance_to(vertex):
            return True
        else:
            return False

    @property
    def top_left_circumsquare_corner(self):
        return tuple([self.center.x - self.radius, self.center.y - self.radius])

    @property
    def bottom_right_circumsquare_corner(self):
        return tuple([self.center.x + self.radius, self.center.y + self.radius])
