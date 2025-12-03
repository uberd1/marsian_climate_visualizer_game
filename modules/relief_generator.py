import numpy as np
from perlin_noise import PerlinNoise


def generate_relief(width: int, height: int, seed: int,
                    octaves: int = 4, amp: float = 10.0, period: int = 32) -> np.ndarray:
    """
    Генерирует 2D-карту высот (рельеф) с использованием шума Перлина.

    :param width: Ширина карты.
    :param height: Высота карты.
    :param seed: Сид для генератора случайных чисел, обеспечивает воспроизводимость.
    :param octaves: Количество октав шума (влияет на детализацию).
    :param amp: Амплитуда (максимальный перепад высот).
    :param period: Период/масштаб (влияет на "размер" гор и долин).
    :return: 2D-массив NumPy с высотами.
    """
    # 1. Инициализация генератора шума с заданными параметрами
    noise = PerlinNoise(octaves=octaves, seed=seed)
    relief_map = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            noise_val = noise([x / period, y / period])
            relief_map[y][x] = noise_val * amp

    return relief_map