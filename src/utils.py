import math

def calculate_hydraulic_resistance(width, height, length, viscosity):
    w = width
    h = height

    if h > w: # switch h and w to make sure the constraints for the channel resistance calculation applies
        h, w = w, h

    # if math.isclose(h, w, rel_tol=0, abs_tol=1e-5):
    #     return 28.4 * viscosity * length / (w**4) 

    # if h < w, then the hydraulic resistance is calculated as follows
    a = (1 - (192 * h / (math.pi**5 * w) * math.tanh(math.pi * w / (2 * h))))
    hydraulic_resistance = 12 * (1 / a) * viscosity * length / (w * h**3) 

    return hydraulic_resistance

def calculate_hydraulic_resistance_cylinder(length, radius, viscosity):
    # Hydraulic resistance for a cylinder
    return (8 * viscosity * length) / (math.pi * radius**4)  

def bisect_root(f, a, b, tol=1e-12, maxiter=100):
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError(f"No sign change in [{a}, {b}]: f(a)={fa}, f(b)={fb}")
    for _ in range(maxiter):
        c = (a + b) / 2
        fc = f(c)
        if abs(fc) < tol:
            return c
        
        if abs(b - a)/2 < tol:
            return c

        # pick the subinterval that still brackets the root
        if fa * fc <= 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return (a + b) / 2
