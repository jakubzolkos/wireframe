import math
from autopcb.datatypes.common import BoundingBox, Vector2D


def distance(p1: Vector2D, p2: Vector2D) -> float:
    """Finds the distance between two points"""
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def angle_between(center: Vector2D, point: Vector2D) -> float:
    """Finds the inverse tangent between two points"""
    return math.atan2(point.y - center.y, point.x - center.x)


def normalize_angle(angle: float) -> float:
    """Make the angle lie between 0 and 360 degrees"""
    return angle % 360 if angle >= 0 else (angle % 360) + 360


def get_arc_bounding_box(start: Vector2D, mid: Vector2D | None, end: Vector2D) -> BoundingBox:
    """Computes the bounding box of an arc

    If mid is None, treats the arc as a straight line from start to end.
    """
    # If mid point is missing, treat as a line
    if mid is None:
        min_x = min(start.x, end.x)
        max_x = max(start.x, end.x)
        min_y = min(start.y, end.y)
        max_y = max(start.y, end.y)
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)

    def find_circle_center(p1: Vector2D, p2: Vector2D, p3: Vector2D) -> Vector2D | None:
        """Finds the position of the center of a circle that the arc defined by three points is a part of"""
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y

        # Determinant (twice the signed area)
        d = 2 * (x1 * (y2 - y3) +
                 x2 * (y3 - y1) +
                 x3 * (y1 - y2))

        # Colinear or nearly colinear -> no finite-radius circle
        if abs(d) < 1e-12:
            return None

        x1_sq_y1_sq = x1 * x1 + y1 * y1
        x2_sq_y2_sq = x2 * x2 + y2 * y2
        x3_sq_y3_sq = x3 * x3 + y3 * y3

        ux = (x1_sq_y1_sq * (y2 - y3) +
              x2_sq_y2_sq * (y3 - y1) +
              x3_sq_y3_sq * (y1 - y2)) / d

        uy = (x1_sq_y1_sq * (x3 - x2) +
              x2_sq_y2_sq * (x1 - x3) +
              x3_sq_y3_sq * (x2 - x1)) / d

        return Vector2D(ux, uy)

    center = find_circle_center(start, mid, end)

    # Degenerate case: points are colinear or extremely close -> treat as polyline bbox
    if center is None:
        xs = [start.x, mid.x, end.x]
        ys = [start.y, mid.y, end.y]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)

    # Circle radius
    radius = math.hypot(start.x - center.x, start.y - center.y)

    # Angles of the points w.r.t. center
    def angle_of(p: Vector2D) -> float:
        return math.atan2(p.y - center.y, p.x - center.x)

    start_angle = angle_of(start)
    mid_angle = angle_of(mid)
    end_angle = angle_of(end)

    TAU = 2 * math.pi

    def angle_on_arc(alpha: float, s: float, m: float, e: float) -> bool:
        """Return True if angle alpha lies on the arc from s to e that passes through m."""
        def norm(a: float) -> float:
            return a % TAU

        s = norm(s)
        m = norm(m)
        e = norm(e)
        alpha = norm(alpha)

        # How far CCW from start to mid/end
        diff_sm = (m - s) % TAU
        diff_se = (e - s) % TAU

        if diff_sm <= diff_se:
            # Arc is CCW from s -> e (mid is on that CCW sweep)
            diff_sa = (alpha - s) % TAU
            return 0.0 <= diff_sa <= diff_se
        else:
            # Arc is CW from s -> e, equivalently CCW from e -> s
            diff_es = (s - e) % TAU
            diff_ea = (alpha - e) % TAU
            return 0.0 <= diff_ea <= diff_es

    # Start, mid, end points are always included
    angles = [start_angle, mid_angle, end_angle]

    # Check the cardinal angles (0, 90, 180, 270 degrees) in radians
    for a in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        if angle_on_arc(a, start_angle, mid_angle, end_angle):
            angles.append(a)

    # Generate all points (start, mid, end, and any cardinal points on the arc)
    points = [
        Vector2D(
            center.x + radius * math.cos(a),
            center.y + radius * math.sin(a),
            )
        for a in angles
    ]

    min_x = min(p.x for p in points)
    max_x = max(p.x for p in points)
    min_y = min(p.y for p in points)
    max_y = max(p.y for p in points)

    return BoundingBox(min_x, min_y, max_x - min_x, max_y - min_y)
