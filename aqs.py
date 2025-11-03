
AQS = [
    [100, 81],
    [80, 61],
    [60, 41],
    [40, 21],
    [20, 0],
]

AQS_CO2 = [
    [400.0, 600.0],
    [601.0, 1000.0],
    [1001.0, 1500.0],
    [1501.0, 2500.0],
    [2501.0, 4000.0],
]

AQS_PM1 = [
    [0.0, 14.0],
    [15.0, 34.0],
    [35.0, 61.0],
    [62.0, 95.0],
    [96.0, 150.0],
]

AQS_PM25 = [
    [0.0, 20.0],
    [21.0, 50.0],
    [51.0, 90.0],
    [91.0, 140.0],
    [141.0, 200.0],
]

AQS_PM10 = [
    [0.0, 30.0],
    [31.0, 75.0],
    [76.0, 125.0],
    [126.0, 200.0],
    [201.0, 300.0],
]

AQS_VOC = [
    [0.0, 0.087],
    [0.088, 0.261],
    [0.262, 0.660],
    [0.661, 2.200],
    [2.201, 3.00],
]

AQS_VOC_INDEX = [
    [1.0, 200.0],
    [201.0, 250.0],
    [251.0, 350.0],
    [351.0, 400.0],
    [401.0, 500.0],
]

AQS_NOX_INDEX = [
    [1.0, 50.0],
    [51.0, 100.0],
    [101.0, 300.0],
    [301.0, 350.0],
    [351.0, 500.0],
]

AQS_MIN = -1


class AQSData:
    def __init__(self, t, i, bp):
        self.t = t
        self.i = i
        self.bp = bp


def get_index_data(value: float, array, aqs_array):
    for i, (low, high) in enumerate(array):
        if low <= value <= high:
            return AQSData(i, aqs_array[i], array[i])
        elif value < low:
            return AQSData(AQS_MIN, aqs_array[0], array[0])
    return AQSData(len(aqs_array), aqs_array[-1], array[-1])


def round_value(n: float, decimals: int = 0) -> float:
    if decimals == 0:
        m = 1.0
    else:
        m = 10.0 ** decimals
    return round(n * m) / m


def get_aqi_general_formula(cp, av, aqia, decimals=0, min_val=100):
    if cp in {65535.0, 6553.5, 65534.0, 6553.4}:
        return 100

    value = round_value(cp, decimals)
    data = get_index_data(value, av, aqia)

    if data.t == len(aqia):
        return 0
    elif data.t == AQS_MIN:
        return min_val

    return round(
        ((data.i[1] - data.i[0]) / (data.bp[1] - data.bp[0]) * (value - data.bp[0])) + data.i[0]
    )


def get_co2(cp: int) -> int:
    return get_aqi_general_formula(cp, AQS_CO2, AQS)


def get_pm1(cp: float) -> int:
    return get_aqi_general_formula(cp, AQS_PM1, AQS)


def get_pm25(cp: float) -> int:
    return get_aqi_general_formula(cp, AQS_PM25, AQS)


def get_pm10(cp: float) -> int:
    return get_aqi_general_formula(cp, AQS_PM10, AQS)


def get_voc_index(cp: int) -> int:
    return get_aqi_general_formula(cp, AQS_VOC_INDEX, AQS)


def get_nox_index(cp: int) -> int:
    return get_aqi_general_formula(cp, AQS_NOX_INDEX, AQS)


def calculate_aqs(co2=None, pm1=None, pm25=None, pm10=None, voc_index=None, nox_index=None) -> int:
    aqs = []
    if co2 is not None:
        aqs.append(get_co2(co2))
    if pm1 is not None:
        aqs.append(get_pm1(pm1))
    if pm25 is not None:
        aqs.append(get_pm25(pm25))
    if pm10 is not None:
        aqs.append(get_pm10(pm10))
    if voc_index is not None:
        aqs.append(get_voc_index(voc_index))
    if nox_index is not None:
        aqs.append(get_nox_index(nox_index))

    return min(aqs) if aqs else 100
