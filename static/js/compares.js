// Весовые коэффициенты для различных характеристик
const WEIGHTS = {
    performance: 0.4,       // Увеличена доля производительности
    camera: 0.2,            // Камера
    battery: 0.15,          // Батарея
    display: 0.15,          // Экран
    connectivity: 0.1,      // Связь
    features: 0.1           // Дополнительные функции
};

// Расширенный справочник мобильных процессоров (CPU_SCORES)
const CPU_SCORES = {
    // Топовые (2024-2025)
    "MediaTek Dimensity 9500": 10.0,    // AnTuTu: 3,500,000 [citation:10]
    "Qualcomm Snapdragon 8 Elite 2": 9.9, // AnTuTu: 2,783,058 [citation:1]
    "MediaTek Dimensity 9400+": 9.8,      // AnTuTu: 2,651,570 [citation:7]
    "Samsung Exynos 2500": 9.6,           // AnTuTu: 2,213,797 [citation:7]
    "MediaTek Dimensity 9400": 9.5,        // AnTuTu: 2,605,867 [citation:7]
    "Apple A18 Pro": 9.4,                 // Geekbench: 3582/9089 [citation:7]
    "Qualcomm Snapdragon 8 Gen 4": 9.3,   // AnTuTu: 2,745,854 [citation:7]
    "MediaTek Dimensity 9300+": 9.2,       // AnTuTu: 2,111,636 [citation:7]
    "MediaTek Dimensity 9300": 9.0,        // AnTuTu: 2,079,810 [citation:7]
    "Qualcomm Snapdragon 8 Gen 3": 8.9,    // AnTuTu: 2,052,774 [citation:7]
    
    // Высокий сегмент
    "Apple A18": 8.8,                     // Geekbench: 3466/8592 [citation:7]
    "Samsung Exynos 2400e": 8.7,          // AnTuTu: 1,781,567 [citation:7]
    "Samsung Exynos 2400": 8.6,           // AnTuTu: 1,744,941 [citation:7]
    "MediaTek Dimensity 8450": 8.5,       // AnTuTu: 1,675,507 [citation:7]
    "Apple A17 Pro": 8.4,                 // Geekbench: 2953/7441 [citation:7]
    "Qualcomm Snapdragon 8s Gen 3": 8.3,  // AnTuTu: 1,488,885 [citation:7]
    "MediaTek Dimensity 8400": 8.2,       // AnTuTu: 1,633,597 [citation:7]
    "Qualcomm Snapdragon 8 Gen 2": 8.1,   // AnTuTu: 1,557,749 [citation:7]
    "Google Tensor G4": 8.0,              // AnTuTu: 1,125,355 [citation:7]
    
    // Средний сегмент
    "MediaTek Dimensity 8350": 7.9,       // AnTuTu: 1,431,343 [citation:7]
    "MediaTek Dimensity 8300": 7.8,       // AnTuTu: 1,406,012 [citation:7]
    "Qualcomm Snapdragon 7+ Gen 3": 7.7,  // AnTuTu: 1,409,887 [citation:7]
    "Apple A16 Bionic": 7.6,              // Geekbench: 2627/6838 [citation:7]
    "Qualcomm Snapdragon 8+ Gen 1": 7.5,  // AnTuTu: 1,299,948 [citation:7]
    "MediaTek Dimensity 9200+": 7.4,      // AnTuTu: 1,489,987 [citation:7]
    "Google Tensor G3": 7.3,              // AnTuTu: 1,152,535 [citation:7]
    "MediaTek Dimensity 9200": 7.2,       // AnTuTu: 1,468,431 [citation:7]
    "Qualcomm Snapdragon 7+ Gen 2": 7.1,  // AnTuTu: 1,124,420 [citation:7]
    
    // Бюджетные
    "Samsung Exynos 2200": 7.0,           // AnTuTu: 1,132,394 [citation:7]
    "MediaTek Dimensity 9000+": 6.9,      // AnTuTu: 1,114,121 [citation:7]
    "MediaTek Dimensity 9000": 6.8,       // AnTuTu: 1,099,019 [citation:7]
    "Apple A15 Bionic": 6.7,              // Geekbench: 2332/5736 [citation:7]
    "Qualcomm Snapdragon 8 Gen 1": 6.6,   // AnTuTu: 1,168,329 [citation:7]
    "Qualcomm Snapdragon 6 Gen 1": 6.0,   // AnTuTu: ~700,000 [citation:1]
    "MediaTek Dimensity 7200": 5.9,       // AnTuTu: ~800,000 [citation:1]
    "MediaTek Helio G99": 5.5,            // AnTuTu: ~500,000 [citation:1]
    "Unisoc T820": 5.0,                   // AnTuTu: ~400,000
    "Unisoc T612": 4.5                    // AnTuTu: ~250,000 [citation:1]
};

// Расширенный справочник мобильных GPU
const GPU_SCORES = {
    // Топовые (2025)
    "Qualcomm Adreno 840": 10.0,         // 3DMark: 27,833 [citation:2]
    "Qualcomm Adreno 830": 9.8,          // 3DMark: 19,883 [citation:1]
    "ARM Mali-G925 Immortalis MP16": 9.7,// GFXBench: 316.5fps [citation:1]
    "Apple M4 10-core GPU": 9.6,         // GFXBench: 399.5fps [citation:1]
    "Apple A18 Pro GPU": 9.5,            // GFXBench: 231.15fps [citation:1]
    "ARM Immortalis-G925 MC12": 9.4,     // GFXBench: 330fps [citation:1]
    "Samsung Xclipse 950": 9.3,          // RDNA 3, аналог Radeon 7900M [citation:1]
    "ARM Immortalis-G720 MP12": 9.2,     // GFXBench: ~250fps [citation:1]
    "Qualcomm Adreno 750": 9.0,          // GFXBench: 248fps [citation:1]
    
    // Высокий сегмент
    "Apple M3 10-Core GPU": 8.9,         // GFXBench: 372fps [citation:1]
    "Samsung Xclipse 940": 8.8,          // GFXBench: 215fps [citation:1]
    "Qualcomm Adreno 740": 8.7,          // GFXBench: 213fps [citation:1]
    "ARM Immortalis-G715 MP11": 8.6,     // GFXBench: 113fps [citation:1]
    "Apple M2 10-Core GPU": 8.5,         // GFXBench: 331.5fps [citation:1]
    "Qualcomm Adreno 735": 8.4,          // GFXBench: 171fps [citation:1]
    "ARM Mali-G715 MP11": 8.3,           // GFXBench: 113fps [citation:1]
    "Apple A17 Pro GPU": 8.2,            // GFXBench: 164fps [citation:1]
    "AMD Radeon 890M": 8.1,              // Лучшая интегрированная графика [citation:8]
    
    // Средний сегмент
    "Qualcomm Adreno 732": 8.0,          // GFXBench: 194.5fps [citation:1]
    "ARM Mali-G720 MP7": 7.9,            // GFXBench: 199fps [citation:1]
    "Qualcomm Adreno 725": 7.8,          // GFXBench: 137fps [citation:1]
    "Apple A16 GPU 5-Core": 7.7,         // GFXBench: 189fps [citation:1]
    "Samsung Xclipse 920": 7.6,          // GFXBench: 125fps [citation:1]
    "ARM Mali-G615 MP6": 7.5,            // GFXBench: 99fps [citation:1]
    "Qualcomm Adreno 720": 7.4,          // GFXBench: 90.5fps [citation:1]
    "ARM Mali-G710 MP10": 7.3,           // GFXBench: 149fps [citation:1]
    "Apple A15 GPU 5-Core": 7.2,         // GFXBench: 152.6fps [citation:1]
    
    // Бюджетные
    "Qualcomm Adreno 660": 7.0,          // GFXBench: 95fps [citation:1]
    "ARM Mali-G57 MC2": 6.8,             // GFXBench: ~60fps [citation:1]
    "PowerVR 7XT GT7600 Plus": 6.5,      // Grade B [citation:4]
    "ARM Mali-G78 MP24": 6.3,            // GFXBench: 112fps [citation:1]
    "Qualcomm Adreno 650": 6.0,          // GFXBench: 88fps [citation:1]
    "ARM Mali-G77 MP11": 5.8,            // GFXBench: 80fps [citation:1]
    "Adreno 618": 5.5,                   // Grade B [citation:4]
    "ARM Mali-G76 MP16": 5.3,            // GFXBench: 53.5fps [citation:1]
    "Mali-G72 MP3": 5.0,                 // Grade C [citation:4]
    "Adreno 505": 4.5,                   // Grade D [citation:4]
    "PowerVR G6430": 4.0                 // Grade D [citation:4]
};

// Правила для оценки характеристик
const SCORE_RULES = {
    // Производительность
    performance: {
        'Оценка AnTuTu': { 
            max: 3500000, 
            min: 100000, 
            weight: 0.4,
            description: "Синтетический тест общей производительности"
        },
        'Geekbench (многоядерное)': { 
            max: 14000, 
            min: 1000, 
            weight: 0.3,
            description: "Бенчмарк многопоточных CPU-операций"
        },
        'Процессор': { 
            values: CPU_SCORES, 
            weight: 0.15,
            matchThreshold: 0.7,
            description: "Рейтинг мобильного процессора"
        },
        'Графический процессор': { 
            values: GPU_SCORES, 
            weight: 0.15,
            matchThreshold: 0.7,
            description: "Рейтинг мобильного GPU"
        }
    },
    
    // Камера
    camera: {
        'Основная камера (Мп)': { 
            max: 200, 
            min: 8, 
            weight: 0.6,
            description: "Разрешение основной камеры"
        },
        'Видеозапись': { 
            values: {
                '8K@30fps': 10,
                '4K@120fps': 9.5,
                '4K@60fps': 9,
                '4K@30fps': 8,
                '1080p@240fps': 7.5,
                '1080p@120fps': 7,
                '1080p@60fps': 6.5,
                '1080p@30fps': 6,
                '720p@30fps': 5
            },
            weight: 0.4,
            description: "Возможности видеосъемки"
        }
    },
    
    // Батарея
    battery: {
        'Емкость батареи (mAh)': { 
            max: 6000, 
            min: 2000, 
            weight: 0.7,
            description: "Общая емкость аккумулятора"
        },
        'Быстрая зарядка': { 
            parse: (value) => {
                const match = value.match(/(\d+)\s*Вт/);
                return match ? parseInt(match[1]) : 0;
            },
            max: 150, 
            min: 5, 
            weight: 0.3,
            description: "Мощность быстрой зарядки"
        }
    },
    
    // Экран
    display: {
        'Размер дисплея (дюймы)': { 
            max: 7.5, 
            min: 4.7, 
            weight: 0.3,
            description: "Диагональ экрана"
        },
        'Плотность пикселей (PPI)': { 
            max: 600, 
            min: 250, 
            weight: 0.3,
            description: "Пиксельная плотность"
        },
        'Тип дисплея': { 
            values: {
                'Dynamic AMOLED 2X': 10,
                'Super AMOLED': 9,
                'AMOLED': 8,
                'OLED': 8,
                'LTPO OLED': 9,
                'MicroLED': 9.5,
                'IPS LCD': 7,
                'TFT LCD': 6
            },
            weight: 0.4,
            description: "Технология производства дисплея"
        }
    },
    
    // Связь
    connectivity: {
        'Поддержка 5G': { 
            values: {
                'Да': 10,
                'Нет': 0
            },
            weight: 0.4,
            description: "Наличие 5G модема"
        },
        'Wi-Fi': { 
            values: {
                'Wi-Fi 7': 10,
                'Wi-Fi 6E': 9,
                'Wi-Fi 6': 8,
                'Wi-Fi 5': 7,
                'Wi-Fi 4': 6
            },
            weight: 0.3,
            description: "Стандарт Wi-Fi"
        },
        'Bluetooth': { 
            values: {
                '5.4': 10,
                '5.3': 9,
                '5.2': 8,
                '5.1': 7,
                '5.0': 6
            },
            weight: 0.3,
            description: "Версия Bluetooth"
        }
    },
    
    // Дополнительные функции
    features: {
        'Защита от воды': { 
            values: {
                'IP68': 10,
                'IP67': 9,
                'IP65': 8,
                'IP54': 7,
                'Нет': 0
            },
            weight: 0.4,
            description: "Степень защиты от воды и пыли"
        },
        'Сканер отпечатков': { 
            values: {
                'Ультразвуковой': 10,
                'Оптический': 8,
                'На кнопке': 7,
                'Нет': 0
            },
            weight: 0.3,
            description: "Тип сканера отпечатков пальцев"
        },
        'NFC': { 
            values: {
                'Да': 10,
                'Нет': 0
            },
            weight: 0.3,
            description: "Наличие NFC для бесконтактных платежей"
        }
    }
};

// Функция для расчета баллов телефона
function calculatePhoneScore(phone) {
    const scores = {
        performance: 0,
        camera: 0,
        battery: 0,
        display: 0,
        connectivity: 0,
        features: 0
    };

    // Производительность
    scores.performance += calculateFeatureScore(phone, 'Оценка AnTuTu', 'performance');
    scores.performance += calculateFeatureScore(phone, 'Geekbench (многоядерное)', 'performance');
    scores.performance += calculateFeatureScore(phone, 'Процессор', 'performance');
    scores.performance += calculateFeatureScore(phone, 'Графический процессор', 'performance');
    
    // Камера
    scores.camera += calculateFeatureScore(phone, 'Основная камера (Мп)', 'camera');
    scores.camera += calculateFeatureScore(phone, 'Видеозапись', 'camera');
    
    // Батарея
    scores.battery += calculateFeatureScore(phone, 'Емкость батареи (mAh)', 'battery');
    scores.battery += calculateFeatureScore(phone, 'Быстрая зарядка', 'battery');
    
    // Экран
    scores.display += calculateFeatureScore(phone, 'Размер дисплея (дюймы)', 'display');
    scores.display += calculateFeatureScore(phone, 'Плотность пикселей (PPI)', 'display');
    scores.display += calculateFeatureScore(phone, 'Тип дисплея', 'display');
    
    // Связь
    scores.connectivity += calculateFeatureScore(phone, 'Поддержка 5G', 'connectivity');
    scores.connectivity += calculateFeatureScore(phone, 'Wi-Fi', 'connectivity');
    scores.connectivity += calculateFeatureScore(phone, 'Bluetooth', 'connectivity');
    
    // Дополнительные функции
    scores.features += calculateFeatureScore(phone, 'Защита от воды', 'features');
    scores.features += calculateFeatureScore(phone, 'Сканер отпечатков', 'features');
    scores.features += calculateFeatureScore(phone, 'NFC', 'features');

    // Рассчитываем общий балл
    let totalScore = 0;
    for (const category in scores) {
        totalScore += scores[category] * WEIGHTS[category];
    }
    
    // Нормализуем до 100 баллов
    totalScore = Math.min(100, Math.round(totalScore * 10));
    
    return {
        total: totalScore,
        categories: scores
    };
}

// Вспомогательная функция для расчета баллов по характеристике
function calculateFeatureScore(phone, feature, category) {
    const rule = SCORE_RULES[category][feature];
    if (!rule || !phone[feature]) return 0;
    
    let value = phone[feature];
    
    // Для числовых значений
    if (rule.max !== undefined && rule.min !== undefined) {
        // Если есть функция для парсинга значения
        if (rule.parse) {
            value = rule.parse(value);
        } else {
            // Пробуем преобразовать в число
            value = parseFloat(value);
            if (isNaN(value)) return 0;
        }
        
        // Нормализация значения
        const normalized = (value - rule.min) / (rule.max - rule.min);
        return Math.min(10, Math.max(0, normalized * 10)) * rule.weight;
    }
    // Для значений из словаря
    else if (rule.values) {
        // Для CPU/GPU используем расширенное сопоставление
        if (feature === 'Процессор' || feature === 'Графический процессор') {
            const bestMatch = findBestMatch(value, rule.values, rule.matchThreshold);
            return bestMatch ? rule.values[bestMatch] * rule.weight : 0;
        }
        
        // Ищем точное совпадение
        for (const [key, score] of Object.entries(rule.values)) {
            if (value.toLowerCase().includes(key.toLowerCase())) {
                return score * rule.weight;
            }
        }
        
        // Ищем частичное совпадение
        for (const [key, score] of Object.entries(rule.values)) {
            const keyLower = key.toLowerCase();
            const valueLower = value.toLowerCase();
            
            if (valueLower.startsWith(keyLower) || 
                valueLower.endsWith(keyLower) || 
                valueLower.includes(keyLower)) {
                return score * rule.weight;
            }
        }
        
        return 0;
    }
    
    return 0;
}

// Функция нечеткого поиска для CPU/GPU
function findBestMatch(input, dictionary, threshold = 0.7) {
    const inputLower = input.toLowerCase().replace(/\s+/g, '');
    let bestMatch = null;
    let bestScore = 0;

    for (const key in dictionary) {
        const keyLower = key.toLowerCase().replace(/\s+/g, '');
        
        // Расчет схожести Jaccard
        const similarity = calculateSimilarity(inputLower, keyLower);
        if (similarity > bestScore && similarity >= threshold) {
            bestScore = similarity;
            bestMatch = key;
        }
    }
    return bestMatch;
}

// Метрика схожести Jaccard
function calculateSimilarity(str1, str2) {
    const set1 = new Set(str1.split(''));
    const set2 = new Set(str2.split(''));
    const intersection = [...set1].filter(x => set2.has(x)).length;
    const union = new Set([...set1, ...set2]).size;
    return union > 0 ? intersection / union : 0;
}

// Функция для сравнения двух телефонов
function comparePhones(phone1, phone2) {
    const score1 = calculatePhoneScore(phone1);
    const score2 = calculatePhoneScore(phone2);
    
    // Определяем победителя
    let winner = null;
    let difference = Math.abs(score1.total - score2.total);
    
    if (score1.total > score2.total) {
        winner = {
            phone: phone1,
            score: score1,
            difference: difference
        };
    } else if (score2.total > score1.total) {
        winner = {
            phone: phone2,
            score: score2,
            difference: difference
        };
    } else {
        winner = null; // Ничья
    }
    
    return {
        phone1: {
            data: phone1,
            score: score1
        },
        phone2: {
            data: phone2,
            score: score2
        },
        winner: winner
    };
}

// Экспортируем функции для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    // Для Node.js
    module.exports = {
        calculatePhoneScore,
        comparePhones,
        CPU_SCORES,
        GPU_SCORES,
        SCORE_RULES,
        findBestMatch
    };
} else {
    // Для браузера
    window.PhoneComparer = {
        calculatePhoneScore,
        comparePhones,
        CPU_SCORES,
        GPU_SCORES,
        SCORE_RULES,
        findBestMatch
    };
}
