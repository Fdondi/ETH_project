def sum(num1, num2):
    return num1 + num2

def sum_only_positive(num1, num2):
    if num1 > 0 and num2 > 0:
        return num1 + num2
    elif num1 > 0:
        return num1
    elif num2 > 0:
        return num2
    return None