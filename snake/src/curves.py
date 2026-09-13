"""Renderer-independent snake smoothing."""

def smooth_centerline(points):
    """Remove staircase oscillation, preserving straight runs and length.

    A symmetric three-point filter cancels alternating horizontal/vertical
    steps. Endpoint extrapolation also smooths the head's trajectory, rather
    than leaving it bouncing between the original grid directions.
    """
    if len(points) < 3:
        return list(points)
    def blend(a, b, c, weights):
        return tuple(sum(p[d]*w for p, w in zip((a,b,c), weights)) for d in (0,1))
    return ([blend(*points[:3], (.75,.5,-.25))] +
            [blend(points[i-1], points[i], points[i+1], (.25,.5,.25))
             for i in range(1, len(points)-1)] +
            [blend(*points[-3:], (-.25,.5,.75))])


def curve_controls(points, i):
    """Cubic handles for the tailward point i to the headward point i-1."""
    a, b = points[i], points[i-1]
    before = points[i+1] if i+1 < len(points) else (2*a[0]-b[0], 2*a[1]-b[1])
    after = points[i-2] if i >= 2 else (2*b[0]-a[0], 2*b[1]-a[1])
    return (tuple(a[d]+(b[d]-before[d])/6 for d in (0,1)),
            tuple(b[d]-(after[d]-a[d])/6 for d in (0,1)))
