"""
Implements the Nelder-Mead algorithm for maximizing a function with one or more
variables.

"""

import numpy as np
from numba import njit
from collections import namedtuple

results = namedtuple('results', 'x fun success nit final_simplex')


@njit
def nelder_mead(fun, x0, bounds=np.array([[], []]).T, args=(), tol_f=1e-10,
                tol_x=1e-10, max_iter=1000):
    """
    .. highlight:: none

    Maximize a scalar-valued function with one or more variables using the
    Nelder-Mead method.

    This function is JIT-compiled in `nopython` mode using Numba.

    Parameters
    ----------
    fun : callable
        The objective function to be maximized: `fun(x, *args) -> float`
        where x is an 1-D array with shape (n,) and args is a tuple of the
        fixed parameters needed to completely specify the function. This
        function must be JIT-compiled in `nopython` mode using Numba.

    x0 : ndarray(float, ndim=1)
        Initial guess. Array of real elements of size (n,), where ānā is the
        number of independent variables.

    bounds: ndarray(float, ndim=2), optional
        Bounds for each variable for proposed solution, encoded as a sequence
        of (min, max) pairs for each element in x. The default option is used
        to specify no bounds on x.

    args : tuple, optional
        Extra arguments passed to the objective function.

    tol_f : scalar(float), optional(default=1e-10)
        Tolerance to be used for the function value convergence test.

    tol_x : scalar(float), optional(default=1e-10)
        Tolerance to be used for the function domain convergence test.

    max_iter : scalar(float), optional(default=1000)
        The maximum number of allowed iterations.

    Returns
    -------
    results : namedtuple
        A namedtuple containing the following items:
        ::

            "x" : Approximate local maximizer
            "fun" : Approximate local maximum value
            "success" : 1 if the algorithm successfully terminated, 0 otherwise
            "nit" : Number of iterations
            "final_simplex" : Vertices of the final simplex

    Examples
    --------
    >>> @njit
    ... def rosenbrock(x):
    ...     return -(100 * (x[1] - x[0] ** 2) ** 2 + (1 - x[0])**2)
    ...
    >>> x0 = np.array([-2, 1])
    >>> qe.optimize.nelder_mead(rosenbrock, x0)
    results(x=array([0.99999814, 0.99999756]), fun=-1.6936258239463265e-10,
            success=True, nit=110,
            final_simplex=array([[0.99998652, 0.9999727],
                                 [1.00000218, 1.00000301],
                                 [0.99999814, 0.99999756]]))

    Notes
    -----
    This algorithm has a long history of successful use in applications, but it
    will usually be slower than an algorithm that uses first or second
    derivative information. In practice, it can have poor performance in
    high-dimensional problems and is not robust to minimizing complicated
    functions. Additionally, there currently is no complete theory describing
    when the algorithm will successfully converge to the minimum, or how fast
    it will if it does.

    References
    ----------

    .. [1] J. C. Lagarias, J. A. Reeds, M. H. Wright and P. E. Wright,
           Convergence Properties of the NelderāMead Simplex Method in Low
           Dimensions, SIAM. J. Optim. 9, 112ā147 (1998).

    .. [2] S. Singer and S. Singer, Efficient implementation of the NelderāMead
           search algorithm, Appl. Numer. Anal. Comput. Math., vol. 1, no. 2,
           pp. 524ā534, 2004.

    .. [3] J. A. Nelder and R. Mead, A simplex method for function
           minimization, Comput. J. 7, 308ā313 (1965).

    .. [4] Gao, F. and Han, L., Implementing the Nelder-Mead simplex algorithm
           with adaptive parameters, Comput Optim Appl (2012) 51: 259.

    .. [5] http://www.scholarpedia.org/article/Nelder-Mead_algorithm

    .. [6] http://www.brnt.eu/phd/node10.html#SECTION00622200000000000000

    .. [7] Chase Coleman's tutorial on Nelder Mead

    .. [8] SciPy's Nelder-Mead implementation

    """
    vertices = _initialize_simplex(x0, bounds)

    results = _nelder_mead_algorithm(fun, vertices, bounds, args=args,
                                     tol_f=tol_f, tol_x=tol_x,
                                     max_iter=max_iter)

    return results


@njit
def _nelder_mead_algorithm(fun, vertices, bounds=np.array([[], []]).T,
                           args=(), Ļ=1., Ļ=2., Ī³=0.5, Ļ=0.5, tol_f=1e-8,
                           tol_x=1e-8, max_iter=1000):
    """
    .. highlight:: none

    Implements the Nelder-Mead algorithm described in Lagarias et al. (1998)
    modified to maximize instead of minimizing. JIT-compiled in `nopython`
    mode using Numba.

    Parameters
    ----------
    fun : callable
        The objective function to be maximized.
            `fun(x, *args) -> float`
        where x is an 1-D array with shape (n,) and args is a tuple of the
        fixed parameters needed to completely specify the function. This
        function must be JIT-compiled in `nopython` mode using Numba.

    vertices : ndarray(float, ndim=2)
        Initial simplex with shape (n+1, n) to be modified in-place.

    args : tuple, optional
        Extra arguments passed to the objective function.

    Ļ : scalar(float), optional(default=1.)
        Reflection parameter. Must be strictly greater than 0.

    Ļ : scalar(float), optional(default=2.)
        Expansion parameter. Must be strictly greater than max(1, Ļ).

    Ī³ : scalar(float), optional(default=0.5)
        Contraction parameter. Must be stricly between 0 and 1.

    Ļ : scalar(float), optional(default=0.5)
        Shrinkage parameter. Must be strictly between 0 and 1.

    tol_f : scalar(float), optional(default=1e-10)
        Tolerance to be used for the function value convergence test.

    tol_x : scalar(float), optional(default=1e-10)
        Tolerance to be used for the function domain convergence test.

    max_iter : scalar(float), optional(default=1000)
        The maximum number of allowed iterations.

    Returns
    -------
    results : namedtuple
        A namedtuple containing the following items:
        ::

            "x" : Approximate solution
            "fun" : Approximate local maximum
            "success" : 1 if successfully terminated, 0 otherwise
            "nit" : Number of iterations
            "final_simplex" : The vertices of the final simplex

    """
    n = vertices.shape[1]
    _check_params(Ļ, Ļ, Ī³, Ļ, bounds, n)

    nit = 0

    ĻĪ³ = Ļ * Ī³
    ĻĻ = Ļ * Ļ
    Ļ_n = Ļ ** n

    f_val = np.empty(n+1, dtype=np.float64)
    for i in range(n+1):
        f_val[i] = _neg_bounded_fun(fun, bounds, vertices[i], args=args)

    # Step 1: Sort
    sort_ind = f_val.argsort()
    LV_ratio = 1

    # Compute centroid
    x_bar = vertices[sort_ind[:n]].sum(axis=0) / n

    while True:
        shrink = False

        # Check termination
        fail = nit >= max_iter

        best_val_idx = sort_ind[0]
        worst_val_idx = sort_ind[n]

        term_f = f_val[worst_val_idx] - f_val[best_val_idx] < tol_f

        # Linearized volume ratio test (see [2])
        term_x = LV_ratio < tol_x

        if term_x or term_f or fail:
            break

        # Step 2: Reflection
        # https://github.com/QuantEcon/QuantEcon.py/issues/530
        temp = Ļ * (x_bar - vertices[worst_val_idx])
        x_r = x_bar + temp
        f_r = _neg_bounded_fun(fun, bounds, x_r, args=args)

        if f_r >= f_val[best_val_idx] and f_r < f_val[sort_ind[n-1]]:
            # Accept reflection
            vertices[worst_val_idx] = x_r
            LV_ratio *= Ļ

        # Step 3: Expansion
        elif f_r < f_val[best_val_idx]:
            # https://github.com/QuantEcon/QuantEcon.py/issues/530
            temp = Ļ * (x_r - x_bar)
            x_e = x_bar + temp
            f_e = _neg_bounded_fun(fun, bounds, x_e, args=args)
            if f_e < f_r:  # Greedy minimization
                vertices[worst_val_idx] = x_e
                LV_ratio *= ĻĻ
            else:
                vertices[worst_val_idx] = x_r
                LV_ratio *= Ļ

        # Step 4 & 5: Contraction and Shrink
        else:
            # Step 4: Contraction
            # https://github.com/QuantEcon/QuantEcon.py/issues/530
            temp = Ī³ * (x_r - x_bar)
            if f_r < f_val[worst_val_idx]:  # Step 4.a: Outside Contraction
                x_c = x_bar + temp
                LV_ratio_update = ĻĪ³
            else:  # Step 4.b: Inside Contraction
                x_c = x_bar - temp
                LV_ratio_update = Ī³

            f_c = _neg_bounded_fun(fun, bounds, x_c, args=args)
            if f_c < min(f_r, f_val[worst_val_idx]):  # Accept contraction
                vertices[worst_val_idx] = x_c
                LV_ratio *= LV_ratio_update

            # Step 5: Shrink
            else:
                shrink = True
                for i in sort_ind[1:]:
                    vertices[i] = vertices[best_val_idx] + Ļ * \
                        (vertices[i] - vertices[best_val_idx])
                    f_val[i] = _neg_bounded_fun(fun, bounds, vertices[i],
                                                args=args)

                sort_ind[1:] = f_val[sort_ind[1:]].argsort() + 1

                x_bar = vertices[best_val_idx] + Ļ * \
                    (x_bar - vertices[best_val_idx]) + \
                    (vertices[worst_val_idx] - vertices[sort_ind[n]]) / n

                LV_ratio *= Ļ_n

        if not shrink:  # Nonshrink ordering rule
            f_val[worst_val_idx] = _neg_bounded_fun(fun, bounds,
                                                    vertices[worst_val_idx],
                                                    args=args)

            for i, j in enumerate(sort_ind):
                if f_val[worst_val_idx] < f_val[j]:
                    sort_ind[i+1:] = sort_ind[i:-1]
                    sort_ind[i] = worst_val_idx
                    break

            x_bar += (vertices[worst_val_idx] - vertices[sort_ind[n]]) / n

        nit += 1

    return results(vertices[sort_ind[0]], -f_val[sort_ind[0]], not fail, nit,
                   vertices)


@njit
def _initialize_simplex(x0, bounds):
    """
    Generates an initial simplex for the Nelder-Mead method. JIT-compiled in
    `nopython` mode using Numba.

    Parameters
    ----------
    x0 : ndarray(float, ndim=1)
        Initial guess. Array of real elements of size (n,), where ānā is the
        number of independent variables.

    bounds: ndarray(float, ndim=2)
        Sequence of (min, max) pairs for each element in x0.

    Returns
    -------
    vertices : ndarray(float, ndim=2)
        Initial simplex with shape (n+1, n).

    """
    n = x0.size

    vertices = np.empty((n + 1, n), dtype=np.float64)

    # Broadcast x0 on row dimension
    vertices[:] = x0

    nonzdelt = 0.05
    zdelt = 0.00025

    for i in range(n):
        # Generate candidate coordinate
        if vertices[i + 1, i] != 0.:
            vertices[i + 1, i] *= (1 + nonzdelt)
        else:
            vertices[i + 1, i] = zdelt

    return vertices


@njit
def _check_params(Ļ, Ļ, Ī³, Ļ, bounds, n):
    """
    Checks whether the parameters for the Nelder-Mead algorithm are valid.
    JIT-compiled in `nopython` mode using Numba.

    Parameters
    ----------
    Ļ : scalar(float)
        Reflection parameter. Must be strictly greater than 0.

    Ļ : scalar(float)
        Expansion parameter. Must be strictly greater than max(1, Ļ).

    Ī³ : scalar(float)
        Contraction parameter. Must be stricly between 0 and 1.

    Ļ : scalar(float)
        Shrinkage parameter. Must be strictly between 0 and 1.

    bounds: ndarray(float, ndim=2)
        Sequence of (min, max) pairs for each element in x.

    n : scalar(int)
        Number of independent variables.

    """
    if Ļ < 0:
        raise ValueError("Ļ must be strictly greater than 0.")
    if Ļ < 1:
        raise ValueError("Ļ must be strictly greater than 1.")
    if Ļ < Ļ:
        raise ValueError("Ļ must be strictly greater than Ļ.")
    if Ī³ < 0 or Ī³ > 1:
        raise ValueError("Ī³ must be strictly between 0 and 1.")
    if Ļ < 0 or Ļ > 1:
        raise ValueError("Ļ must be strictly between 0 and 1.")

    if not (bounds.shape == (0, 2) or bounds.shape == (n, 2)):
        raise ValueError("The shape of `bounds` is not valid.")
    if (np.atleast_2d(bounds)[:, 0] > np.atleast_2d(bounds)[:, 1]).any():
        raise ValueError("Lower bounds must be greater than upper bounds.")


@njit
def _check_bounds(x, bounds):
    """
    Checks whether `x` is within `bounds`. JIT-compiled in `nopython` mode
    using Numba.

    Parameters
    ----------
    x : ndarray(float, ndim=1)
        1-D array with shape (n,) of independent variables.

    bounds: ndarray(float, ndim=2)
        Sequence of (min, max) pairs for each element in x.

    Returns
    -------
    bool
        `True` if `x` is within `bounds`, `False` otherwise.

    """
    if bounds.shape == (0, 2):
        return True
    else:
        return ((np.atleast_2d(bounds)[:, 0] <= x).all() and
                (x <= np.atleast_2d(bounds)[:, 1]).all())


@njit
def _neg_bounded_fun(fun, bounds, x, args=()):
    """
    Wrapper for bounding and taking the negative of `fun` for the
    Nelder-Mead algorithm. JIT-compiled in `nopython` mode using Numba.

    Parameters
    ----------
    fun : callable
        The objective function to be minimized.
            `fun(x, *args) -> float`
        where x is an 1-D array with shape (n,) and args is a tuple of the
        fixed parameters needed to completely specify the function. This
        function must be JIT-compiled in `nopython` mode using Numba.

    bounds: ndarray(float, ndim=2)
        Sequence of (min, max) pairs for each element in x.

    x : ndarray(float, ndim=1)
        1-D array with shape (n,) of independent variables at which `fun` is
        to be evaluated.

    args : tuple, optional
        Extra arguments passed to the objective function.

    Returns
    -------
    scalar
        `-fun(x, *args)` if x is within `bounds`, `np.inf` otherwise.

    """
    if _check_bounds(x, bounds):
        return -fun(x, *args)
    else:
        return np.inf
