import math
import random
from typing import List, NoReturn

from autopcb.datatypes.common import Coordinate, Edge, Triangle, Vector2D, StandardLine


def get_line_intersection(l1: StandardLine, l2: StandardLine) -> Vector2D:
    """
    Get the intersection Vector2D of 2 StandardLines

    :param l1: StandardLine l1
    :param l2: StandardLine l2
    :return: the intersection Vector2D between l1 and l2
    """
    determinant = l1.A * l2.B - l2.A * l1.B
    if determinant == 0:  # The lines are parallel
        raise ValueError(f"The lines {l1} and {l2} do not intersect.")
    else:
        return Vector2D(x=(l2.B * l1.C - l1.B * l2.C) / determinant, y=(l1.A * l2.C - l2.A * l1.C) / determinant)


def _remove_triangles(triangles: List[Triangle], pre_remove: List[Triangle]) -> NoReturn:
    """
    Helper method to remove triangles from triangle list

    :param triangles: the list items should be removed from
    :param pre_remove: the list of items that should be removed from triangles
    :return: nothing. the list is being altered in place.
    """

    for triangle in pre_remove:
        try:
            triangles.remove(triangle)
        except ValueError:
            pass


def scatter_vertices(plane_width: int, plane_height: int, spacing: int, scatter: float) -> List[Vector2D]:
    """
    helper method to scatter random vertices on a specified plane.
    Distance is calculated using the given spacing and scatter.

    :param plane_width: the width of the plane.
    :param plane_height: the height of the plane.
    :param spacing: the spacing between the vertices.
    :param scatter: the scatter multiplier amount the spacing differs from its given value.
    :return: vertex list
    """

    vertices: List[Vector2D] = []
    x_offset = (plane_width % spacing) / 2
    y_offset = (plane_height % spacing) / 2
    for x in range(math.floor((plane_width / spacing) + 1)):
        for y in range(math.floor((plane_height / spacing) + 1)):
            vertices.append(
                Vector2D(
                    x=x_offset + spacing * (x + scatter * (random.random() - 0.5)),
                    y=y_offset + spacing * (y + scatter * (random.random() - 0.5)),
                )
            )
    return vertices


def get_super_triangle(vertices: List[Vector2D]) -> Triangle:
    """
    Get super triangle for vertices

    :param vertices: the vertices the super triangle should encompass.
    :return: the super triangle.
    """

    x = Coordinate(min=math.inf, max=-math.inf)
    y = Coordinate(min=math.inf, max=-math.inf)

    for vertex in vertices:
        if vertex.x < x.min:
            x.min = vertex.x
        if vertex.x > x.max:
            x.max = vertex.x
        if vertex.y < y.min:
            y.min = vertex.y
        if vertex.y > y.max:
            y.max = vertex.y

    max_diff = max(x.diff, y.diff)

    return Triangle(
        Vector2D(x=x.center - 20 * max_diff, y=y.center - max_diff),
        Vector2D(x=x.center, y=y.center + 20 * max_diff),
        Vector2D(x=x.center + 20 * max_diff, y=y.center - max_diff),
        is_super=True,
    )


def delaunay(vertices: List[Vector2D], delete_super_shared: bool = True) -> List[Triangle]:
    """
    Delaunay Triangulate a list of vertices using the Bowyer-Watson algorithm.

    :param vertices: the vertices to triangulate.
    :param delete_super_shared: delete triangles that share vertices with the super triangle
    :return: the list of created triangles.
    """

    # sort vertices by their x-coordinate to improve performance.
    vertices = sorted(vertices, key=lambda vertex: vertex.x)

    # create super triangle from vertices
    super_triangle = get_super_triangle(vertices=vertices)

    # initialise triangle list
    triangles: List[Triangle] = [super_triangle]

    # add super triangle vertices to vertex list
    vertices += super_triangle.vertices

    # initialise triangle removal list
    pre_removed_triangles: List[Triangle] = []

    for vertex in vertices:  # for each vertex

        # initialise list for illegal triangles
        # (triangles whose circumcircle encompasses the vertex)
        illegal_triangles = []

        for triangle in triangles:  # for each triangle
            try:
                # try to create circumcircle
                circumcircle = triangle.circumcircle

                # if the triangle of the current iteration encompasses the vertex
                # -> add triangle to illegal triangles
                if circumcircle.encompasses_vertex(vertex=vertex):
                    illegal_triangles.append(triangle)
            except ValueError:
                # cannot draw circumcircle because the perpendicular bisectors don't intersect
                # -> add the triangle to removal list
                pre_removed_triangles.append(triangle)

        # remove all triangles from triangle list that were added to triangle removal list
        _remove_triangles(triangles=triangles, pre_remove=pre_removed_triangles)

        # initialise shell polygon edge list
        polygon: List[Edge] = []

        # initialise illegal edge list
        illegal_edges = []

        # add all triangle edges from illegal triangles to illegal edges
        for triangle in illegal_triangles:
            illegal_edges += triangle.edges

        for triangle in illegal_triangles:  # for each triangle in illegal triangles
            for edge in triangle.edges:  # for each edge in illegal edges

                # if the edge is unique
                # -> add the edge to the shell polygon
                if illegal_edges.count(edge) == 1:
                    polygon.append(edge)

        # remove all illegal triangles from triangle list
        for triangle in illegal_triangles:
            triangles.remove(triangle)

        for edge in polygon:  # for each edge in shell polygon
            # create new triangles from edge and vertex
            new_triangle = Triangle(a=edge.a, b=edge.b, c=vertex)

            # add the newly created triangle to triangle iterator
            triangles.append(new_triangle)

    # delete all triangles that share vertices with the super triangle
    if delete_super_shared:
        for triangle in triangles:  # for each triangle

            # if the triangle is the super triangle
            # -> add the triangle to removal list
            if triangle.is_super:
                pre_removed_triangles.append(triangle)

            for vertex in triangle.vertices:  # for each vertex in the triangle

                # if the super triangle contains this vertex
                # -> remove the triangle
                if vertex in super_triangle.vertices:
                    try:
                        pre_removed_triangles.append(triangle)
                    except ValueError:
                        pass

    # remove all triangles from triangle list that were added to triangle removal list
    _remove_triangles(triangles=triangles, pre_remove=pre_removed_triangles)

    return triangles  # return triangles
