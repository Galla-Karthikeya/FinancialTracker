def calculate_sip(p, rate, years):
    r = rate / 12 / 100
    n = years * 12
    fv = p * (((1 + r) ** n - 1) / r) * (1 + r)
    invested = p * n
    return round(fv, 2), round(fv - invested, 2), invested


def calculate_mutual_fund_lumpsum(p, rate, years):
    r = rate / 100
    fv = p * ((1 + r) ** years)
    return round(fv, 2), round(fv - p, 2)


def calculate_fd(p, rate, years, compoundings_per_year=4):
    r = rate / 100
    n = compoundings_per_year
    t = years
    amount = p * (1 + r/n)**(n*t)
    return round(amount, 2), round(amount - p, 2)


def calculate_rd(p, rate, months):
    r = rate / 100 / 12
    n = months
    maturity = p * n + p * n * (n + 1) * r / 2
    return round(maturity, 2), round(maturity - p * n, 2)


# Same for EMI, Home Loan EMI
def calculate_emi(principal, rate, years):
    r = rate / (12 * 100)
    n = years * 12
    emi = (principal * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1)
    total_payment = emi * n
    interest = total_payment - principal
    return round(emi, 2), round(total_payment, 2), round(interest, 2)


def calculate_inhand_salary(basic, hra, other_allowances, tax=0, pt=200):
    epf = basic * 0.12
    gross = basic + hra + other_allowances
    net = gross - epf - tax - pt
    return round(net, 2), round(gross, 2), round(epf + tax + pt, 2)

def calculate_new_regime_tax(income):
    slabs = [(0, 300000, 0), (300001, 600000, 0.05),
             (600001, 900000, 0.10), (900001, 1200000, 0.15),
             (1200001, 1500000, 0.20), (1500001, float('inf'), 0.30)]

    income = income - 50000
    tax = 0
    for lower, upper, rate in slabs:
        if income > lower:
            taxable = min(upper, income) - lower
            tax += taxable * rate
    return round(max(tax, 0), 2)

