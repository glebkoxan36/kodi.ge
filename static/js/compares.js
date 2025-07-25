// Весовые коэффициенты для различных характеристик
const WEIGHTS = {
    performance: 0.3,       // Производительность
    camera: 0.2,            // Камера
    battery: 0.15,          // Батарея
    display: 0.15,          // Экран
    connectivity: 0.1,      // Связь
    features: 0.1           // Дополнительные функции
};

// Правила для оценки характеристик
const SCORE_RULES = {
    // Производительность
    'Оценка AnTuTu': {
        max: 2000000,
        min: 100000,
        weight: 0.7
    },
    'Geekbench (многоядерное)': {
        max: 10000,
        min: 1000,
        weight: 0.3
    },
    
    // Камера
    'Основная камера (Мп)': {
        max: 200,
        min: 8,
        weight: 0.6
    },
    'Видеозапись': {
        values: {
            '8K@30fps': 10,
            '4K@60fps': 9,
            '4K@30fps': 8,
            '1080p@60fps': 7,
            '1080p@30fps': 6,
            '720p@30fps': 5
        },
        weight: 0.4
    },
    
    // Батарея
    'Емкость батареи (mAh)': {
        max: 6000,
        min: 2000,
        weight: 0.7
    },
    'Быстрая зарядка': {
        parse: (value) => {
            const match = value.match(/(\d+)\s*Вт/);
            return match ? parseInt(match[1]) : 0;
        },
        max: 100,
        min: 5,
        weight: 0.3
    },
    
    // Экран
    'Размер дисплея (дюймы)': {
        max: 7.5,
        min: 4.7,
        weight: 0.3
    },
    'Плотность пикселей (PPI)': {
        max: 600,
        min: 250,
        weight: 0.3
    },
    'Тип дисплея': {
        values: {
            'Dynamic AMOLED 2X': 10,
            'Super AMOLED': 9,
            'AMOLED': 8,
            'OLED': 8,
            'LTPO OLED': 9,
            'IPS LCD': 7,
            'TFT LCD': 6
        },
        weight: 0.4
    },
    
    // Связь
    'Поддержка 5G': {
        values: {
            'Да': 10,
            'Нет': 0
        },
        weight: 0.4
    },
    'Wi-Fi': {
        values: {
            'Wi-Fi 7': 10,
            'Wi-Fi 6E': 9,
            'Wi-Fi 6': 8,
            'Wi-Fi 5': 7,
            'Wi-Fi 4': 6
        },
        weight: 0.3
    },
    'Bluetooth': {
        values: {
            '5.3': 10,
            '5.2': 9,
            '5.1': 8,
            '5.0': 7,
            '4.2': 6
        },
        weight: 0.3
    },
    
    // Дополнительные функции
    'Защита от воды': {
        values: {
            'IP68': 10,
            'IP67': 9,
            'IP65': 8,
            'IP54': 7,
            'Нет': 0
        },
        weight: 0.4
    },
    'Сканер отпечатков': {
        values: {
            'Ультразвуковой': 10,
            'Оптический': 8,
            'На кнопке': 7,
            'Нет': 0
        },
        weight: 0.3
    },
    'NFC': {
        values: {
            'Да': 10,
            'Нет': 0
        },
        weight: 0.3
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
    const rule = SCORE_RULES[feature];
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
        comparePhones
    };
} else {
    // Для браузера
    window.PhoneComparer = {
        calculatePhoneScore,
        comparePhones
    };
        }
