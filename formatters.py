"""
Shared formatting functions for numbers, currency, percentages.
Single source of truth — all other scripts should import from here.
"""


def fmt(n):
    """Format integer with thousands separator. e.g., 1000 → '1,000'"""
    return f"{int(n):,}"


def fmt_wan(n):
    """Format as ¥X.X万. e.g., 123456 → '¥12.3万'"""
    return f"¥{n/10000:,.1f}万"


def fmt_yuan(n):
    """Format as ¥X (no decimals). e.g., 1234 → '¥1,234'"""
    return f"¥{n:,.0f}"


def fmt_gsv(n):
    """Alias for fmt_yuan — format GSV as ¥X."""
    return f"¥{n:,.0f}"


def fmt_money(v):
    """
    Smart money formatter: >=1万 shows as ¥X.X万, else shows as ¥X,XXX.
    e.g., 12345678 → '¥1234.6万', 5000 → '¥5,000'
    """
    v = round(float(v), 2)
    if abs(v) >= 10000:
        return f'¥{v/10000:.1f}万'
    if v == int(v):
        return f'¥{int(v):,}'
    return f'¥{v:,.2f}'


def fmt_num(v):
    """
    Smart number formatter: >=1M shows as X.X百万, >=1万 shows as X.X万.
    e.g., 1234567 → '1.2百万', 12345 → '1.2万'
    """
    v = round(float(v))
    if abs(v) >= 1000000:
        return f'{v/1000000:.1f}百万'
    if abs(v) >= 10000:
        return f'{v/10000:.1f}万'
    return f'{int(v):,}'


def fmt_roi(v):
    """Format ROI with 2 decimal places. e.g., 15.05 → '15.05'"""
    return f'{v:.2f}'


def fmt_pct(v, decimals=2):
    """Format percentage. e.g., 7.23 → '7.23%'"""
    return f'{v:.{decimals}f}%'


def diff_str(d):
    """Format order difference with team labels. e.g., 100 → '我方+100'"""
    if d > 0:
        return f'我方+{fmt(d)}'
    elif d < 0:
        return f'竞对+{fmt(abs(d))}'
    return '持平'


def diff_class(d):
    """Return CSS color class for order difference: green/red/empty."""
    if d > 0:
        return 'var(--clr-green)'
    elif d < 0:
        return 'var(--clr-red)'
    return ''
