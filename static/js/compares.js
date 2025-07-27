// Моковые данные для тестирования
const mockPhones = [
    {
        "_id": "68671365171ebd407dffe0c0",
        "Бренд": "Samsung",
        "Модель": "Galaxy S24 Ultra",
        "Год выпуска": "2024",
        "ОС": "Android",
        "Версия ОС": "14",
        "Размер дисплея (дюймы)": "6.8",
        "Тип дисплея": "Dynamic AMOLED 2X",
        "Процессор": "Qualcomm Snapdragon 8 Gen 3",
        "Графический процессор": "Adreno 750",
        "ОЗУ (ГБ)": "12",
        "ПЗУ (ГБ)": "256",
        "Основная камера (Мп)": "200",
        "Фронтальная камера (Мп)": "12",
        "Емкость батареи (mAh)": "5000",
        "Текущая цена (руб)": "139990",
        "Оценка AnTuTu": "2050000",
        "Geekbench (многоядерное)": "7100",
        "Изображение": "https://via.placeholder.com/50x50?text=S24U"
    },
    {
        "_id": "1234567890abcdef12345678",
        "Бренд": "Apple",
        "Модель": "iPhone 15 Pro Max",
        "Год выпуска": "2023",
        "ОС": "iOS",
        "Версия ОС": "17",
        "Размер дисплея (дюймы)": "6.7",
        "Тип дисплея": "Super Retina XDR",
        "Процессор": "Apple A17 Pro",
        "Графический процессор": "Apple GPU",
        "ОЗУ (ГБ)": "8",
        "ПЗУ (ГБ)": "256",
        "Основная камера (Мп)": "48",
        "Фронтальная камера (Мп)": "12",
        "Емкость батареи (mAh)": "4422",
        "Текущая цена (руб)": "129990",
        "Оценка AnTuTu": "1850000",
        "Geekbench (м многоядерное)": "6500",
        "Изображение": "https://via.placeholder.com/50x50?text=iPhone"
    },
    {
        "_id": "abcdef123456789012345678",
        "Бренд": "Xiaomi",
        "Модель": "13 Pro",
        "Год выпуска": "2023",
        "ОС": "Android",
        "Версия ОС": "13",
        "Размер дисплея (дюймы)": "6.73",
        "Тип дисплея": "AMOLED",
        "Процессор": "Snapdragon 8 Gen 2",
        "Графический процессор": "Adreno 740",
        "ОЗУ (ГБ)": "12",
        "ПЗУ (ГБ)": "256",
        "Основная камера (Мп)": "50",
        "Фронтальная камера (Мп)": "32",
        "Емкость батареи (mAh)": "4820",
        "Текущая цена (руб)": "89990",
        "Оценка AnTuTu": "1650000",
        "Geekbench (многоядерное)": "5800",
        "Изображение": "https://via.placeholder.com/50x50?text=Xiaomi"
    }
];

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
    "MediaTek Dimensity 9500": 10.0,    // AnTuTu: 3,500,000 
    "Qualcomm Snapdragon 8 Elite 2": 9.9, // AnTuTu: 2,783,058 
    "MediaTek Dimensity 9400+": 9.8,      // AnTuTu: 2,651,570 
    "Samsung Exynos 2500": 9.6,           // AnTuTu: 2,213,797 
    "MediaTek Dimensity 9400": 9.5,        // AnTuTu: 2,605,867 
    "Apple A18 Pro": 9.4,                 // Geekbench: 3582/9089 
    "Qualcomm Snapdragon 8 Gen 4": 9.3,   // AnTuTu: 2,745,854 
    "MediaTek Dimensity 9300+": 9.2,       // AnTuTu: 2,111,636 
    "MediaTek Dimensity 9300": 9.0,        // AnTuTu: 2,079,810 
    "Qualcomm Snapdragon 8 Gen 3": 8.9,    // AnTuTu: 2,052,774 
    
    // Высокий сегмент
    "Apple A18": 8.8,                     // Geekbench: 3466/8592 
    "Samsung Exynos 2400e": 8.7,          // AnTuTu: 1,781,567 
    "Samsung Exynos 2400": 8.6,           // AnTuTu: 1,744,941 
    "MediaTek Dimensity 8450": 8.5,       // AnTuTu: 1,675,507 
    "Apple A17 Pro": 8.4,                 // Geekbench: 2953/7441 
    "Qualcomm Snapdragon 8s Gen 3": 8.3,  // AnTuTu: 1,488,885 
    "MediaTek Dimensity 8400": 8.2,       // AnTuTu: 1,633,597 
    "Qualcomm Snapdragon 8 Gen 2": 8.1,   // AnTuTu: 1,557,749 
    "Google Tensor G4": 8.0,              // AnTuTu: 1,125,355 
    
    // Средний сегмент
    "MediaTek Dimensity 8350": 7.9,       // AnTuTu: 1,431,343 
    "MediaTek Dimensity 8300": 7.8,       // AnTuTu: 1,406,012 
    "Qualcomm Snapdragon 7+ Gen 3": 7.7,  // AnTuTu: 1,409,887 
    "Apple A16 Bionic": 7.6,              // Geekbench: 2627/6838 
    "Qualcomm Snapdragon 8+ Gen 1": 7.5,  // AnTuTu: 1,299,948 
    "MediaTek Dimensity 9200+": 7.4,      // AnTuTu: 1,489,987 
    "Google Tensor G3": 7.3,              // AnTuTu: 1,152,535 
    "MediaTek Dimensity 9200": 7.2,       // AnTuTu: 1,468,431 
    "Qualcomm Snapdragon 7+ Gen 2": 7.1,  // AnTuTu: 1,124,420 
    
    // Бюджетные
    "Samsung Exynos 2200": 7.0,           // AnTuTu: 1,132,394 
    "MediaTek Dimensity 9000+": 6.9,      // AnTuTu: 1,114,121 
    "MediaTek Dimensity 9000": 6.8,       // AnTuTu: 1,099,019 
    "Apple A15 Bionic": 6.7,              // Geekbench: 2332/5736 
    "Qualcomm Snapdragon 8 Gen 1": 6.6,   // AnTuTu: 1,168,329 
    "Qualcomm Snapdragon 6 Gen 1": 6.0,   // AnTuTu: ~700,000 
    "MediaTek Dimensity 7200": 5.9,       // AnTuTu: ~800,000 
    "MediaTek Helio G99": 5.5,            // AnTuTu: ~500,000 
    "Unisoc T820": 5.0,                   // AnTuTu: ~400,000
    "Unisoc T612": 4.5                    // AnTuTu: ~250,000 
};

// Расширенный справочник мобильных GPU
const GPU_SCORES = {
    // Топовые (2025)
    "Qualcomm Adreno 840": 10.0,         // 3DMark: 27,833 
    "Qualcomm Adreno 830": 9.8,          // 3DMark: 19,883 
    "ARM Mali-G925 Immortalis MP16": 9.7,// GFXBench: 316.5fps 
    "Apple M4 10-core GPU": 9.6,         // GFXBench: 399.5fps 
    "Apple A18 Pro GPU": 9.5,            // GFXBench: 231.15fps 
    "ARM Immortalis-G925 MC12": 9.4,     // GFXBench: 330fps 
    "Samsung Xclipse 950": 9.3,          // RDNA 3, аналог Radeon 7900M 
    "ARM Immortalis-G720 MP12": 9.2,     // GFXBench: ~250fps 
    "Qualcomm Adreno 750": 9.0,          // GFXBench: 248fps 
    
    // Высокий сегмент
    "Apple M3 10-Core GPU": 8.9,         // GFXBench: 372fps 
    "Samsung Xclipse 940": 8.8,          // GFXBench: 215fps 
    "Qualcomm Adreno 740": 8.7,          // GFXBench: 213fps 
    "ARM Immortalis-G715 MP11": 8.6,     // GFXBench: 113fps 
    "Apple M2 10-Core GPU": 8.5,         // GFXBench: 331.5fps 
    "Qualcomm Adreno 735": 8.4,          // GFXBench: 171fps 
    "ARM Mali-G715 MP11": 8.3,           // GFXBench: 113fps 
    "Apple A17 Pro GPU": 8.2,            // GFXBench: 164fps 
    "AMD Radeon 890M": 8.1,              // Лучшая интегрированная графика 
    
    // Средний сегмент
    "Qualcomm Adreno 732": 8.0,          // GFXBench: 194.5fps 
    "ARM Mali-G720 MP7": 7.9,            // GFXBench: 199fps 
    "Qualcomm Adreno 725": 7.8,          // GFXBench: 137fps 
    "Apple A16 GPU 5-Core": 7.7,         // GFXBench: 189fps 
    "Samsung Xclipse 920": 7.6,          // GFXBench: 125fps 
    "ARM Mali-G615 MP6": 7.5,            // GFXBench: 99fps 
    "Qualcomm Adreno 720": 7.4,          // GFXBench: 90.5fps 
    "ARM Mali-G710 MP10": 7.3,           // GFXBench: 149fps 
    "Apple A15 GPU 5-Core": 7.2,         // GFXBench: 152.6fps 
    
    // Бюджетные
    "Qualcomm Adreno 660": 7.0,          // GFXBench: 95fps 
    "ARM Mali-G57 MC2": 6.8,             // GFXBench: ~60fps 
    "PowerVR 7XT GT7600 Plus": 6.5,      // Grade B 
    "ARM Mali-G78 MP24": 6.3,            // GFXBench: 112fps 
    "Qualcomm Adreno 650": 6.0,          // GFXBench: 88fps 
    "ARM Mali-G77 MP11": 5.8,            // GFXBench: 80fps 
    "Adreno 618": 5.5,                   // Grade B 
    "ARM Mali-G76 MP16": 5.3,            // GFXBench: 53.5fps 
    "Mali-G72 MP3": 5.0,                 // Grade C 
    "Adreno 505": 4.5,                   // Grade D 
    "PowerVR G6430": 4.0                 // Grade D 
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

// Функция для имитации поиска по API
async function searchPhonesApi(query) {
    return new Promise((resolve) => {
        // Имитация задержки сети
        setTimeout(() => {
            const results = mockPhones.filter(phone => {
                const searchString = `${phone.Бренд} ${phone.Модель}`.toLowerCase();
                return searchString.includes(query.toLowerCase());
            });
            resolve(results);
        }, 300); // Имитация задержки сети 300мс
    });
}

// Объекты для хранения данных о телефонах
let phone1 = null;
let phone2 = null;

// Таймеры для задержки поиска
let searchTimer1 = null;
let searchTimer2 = null;

// Элементы DOM
const phone1Search = document.getElementById('phone1-modal-search');
const phone2Search = document.getElementById('phone2-modal-search');
const phone1Results = document.getElementById('phone1-modal-results');
const phone2Results = document.getElementById('phone2-modal-results');
const phone1Clear = document.getElementById('phone1-clear');
const phone2Clear = document.getElementById('phone2-clear');
const compareBtn = document.getElementById('compare-phones');
const resultsSection = document.getElementById('results-section');

// Модальные окна
const modal1 = document.getElementById('phone1-modal');
const modal2 = document.getElementById('phone2-modal');

// Кнопки выбора телефонов
const selectPhone1Btn = document.getElementById('select-phone1-btn');
const selectPhone2Btn = document.getElementById('select-phone2-btn');

// Обработчики событий
phone1Search.addEventListener('input', () => handleSearchInput(1));
phone2Search.addEventListener('input', () => handleSearchInput(2));
phone1Clear.addEventListener('click', () => clearPhoneSelection(1));
phone2Clear.addEventListener('click', () => clearPhoneSelection(2));
compareBtn.addEventListener('click', comparePhonesHandler);
selectPhone1Btn.addEventListener('click', () => modal1.style.display = 'block');
selectPhone2Btn.addEventListener('click', () => modal2.style.display = 'block');

// Закрытие модальных окон
document.querySelectorAll('.close-modal').forEach(closeBtn => {
    closeBtn.addEventListener('click', function() {
        this.closest('.modal').style.display = 'none';
    });
});

// Закрытие модальных окон при клике вне области
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
});

// Обработка ввода в поле поиска модального окна
function handleSearchInput(phoneNumber) {
    const input = phoneNumber === 1 ? phone1Search : phone2Search;
    const resultsContainer = phoneNumber === 1 ? phone1Results : phone2Results;
    
    const query = input.value.trim();
    
    // Скрываем результаты, если запрос пустой
    if (!query) {
        resultsContainer.style.display = 'none';
        return;
    }
    
    // Показываем загрузку
    resultsContainer.innerHTML = '<div class="loader"><i class="fas fa-spinner"></i> ტელეფონების ძებნა...</div>';
    resultsContainer.style.display = 'block';
    
    // Очищаем предыдущий таймер
    if (phoneNumber === 1) clearTimeout(searchTimer1);
    else clearTimeout(searchTimer2);
    
    // Устанавливаем новый таймер для задержки запроса
    const timer = setTimeout(() => {
        searchPhones(query, phoneNumber);
    }, 300);
    
    if (phoneNumber === 1) searchTimer1 = timer;
    else searchTimer2 = timer;
}

// Поиск телефонов в базе данных
async function searchPhones(query, phoneNumber) {
    const resultsContainer = phoneNumber === 1 ? phone1Results : phone2Results;
    
    try {
        const data = await searchPhonesApi(query);
        
        if (data.length === 0) {
            resultsContainer.innerHTML = '<div class="no-results">ტელეფონები არ მოიძებნა</div>';
            return;
        }
        
        let resultsHTML = '';
        data.forEach(phone => {
            const imageUrl = phone.Изображение || 'https://via.placeholder.com/50x50?text=📱';
            const year = phone['Год выпуска'] || '-';
            
            resultsHTML += `
                <div class="result-item" data-id="${phone._id}" data-phone='${JSON.stringify(phone)}'>
                    <img src="${imageUrl}" alt="${phone.Бренд} ${phone.Модель}">
                    <div class="result-info">
                        <div class="result-brand">${phone.Бренд}</div>
                        <div class="result-model">${phone.Модель}</div>
                    </div>
                    <div class="result-year">${year}</div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = resultsHTML;
        
        // Добавляем обработчики выбора
        document.querySelectorAll(`#phone${phoneNumber}-modal-results .result-item`).forEach(item => {
            item.addEventListener('click', () => {
                selectPhone(item, phoneNumber);
                if (phoneNumber === 1) modal1.style.display = 'none';
                else modal2.style.display = 'none';
            });
        });
    } catch (error) {
        console.error('Ошибка поиска:', error);
        resultsContainer.innerHTML = '<div class="no-results">ძებნის შეცდომა. სცადეთ მოგვიანებით.</div>';
    }
}

// Выбор телефона из результатов поиска
function selectPhone(element, phoneNumber) {
    const phone = JSON.parse(element.dataset.phone);
    
    if (phoneNumber === 1) {
        phone1 = phone;
        document.getElementById('selected-phone1-name').textContent = `${phone.Бренд} ${phone.Модель}`;
        document.getElementById('selected-phone1-img').src = phone.Изображение || 'https://via.placeholder.com/50x50?text=📱';
        document.getElementById('selected-phone1').style.display = 'flex';
    } else {
        phone2 = phone;
        document.getElementById('selected-phone2-name').textContent = `${phone.Бренд} ${phone.Модель}`;
        document.getElementById('selected-phone2-img').src = phone.Изображение || 'https://via.placeholder.com/50x50?text=📱';
        document.getElementById('selected-phone2').style.display = 'flex';
    }
    
    displayPhoneDetails(phone, phoneNumber);
    
    // Активируем кнопку сравнения если выбраны оба телефона
    if (phone1 && phone2) {
        compareBtn.disabled = false;
    }
}

// Очистка выбранного телефона
function clearPhoneSelection(phoneNumber) {
    if (phoneNumber === 1) {
        phone1 = null;
        document.getElementById('selected-phone1').style.display = 'none';
        document.getElementById('phone1-title').textContent = 'ტელეფონი 1';
        document.getElementById('phone1-specs').innerHTML = '';
        document.getElementById('phone1-img').src = '';
    } else {
        phone2 = null;
        document.getElementById('selected-phone2').style.display = 'none';
        document.getElementById('phone2-title').textContent = 'ტელეფონი 2';
        document.getElementById('phone2-specs').innerHTML = '';
        document.getElementById('phone2-img').src = '';
    }
    
    compareBtn.disabled = !(phone1 && phone2);
    
    // Скрываем результаты, если очищены оба телефона
    if (!phone1 && !phone2) {
        resultsSection.style.display = 'none';
    }
}

// Отображение деталей телефона с группировкой
function displayPhoneDetails(phone, phoneNumber) {
    const titleElement = document.getElementById(`phone${phoneNumber}-title`);
    const imgElement = document.getElementById(`phone${phoneNumber}-img`);
    const specsElement = document.getElementById(`phone${phoneNumber}-specs`);
    
    titleElement.textContent = `${phone.Бренд} ${phone.Модель}`;
    
    // Используем изображение из базы, если есть
    imgElement.src = phone.Изображение || 'https://via.placeholder.com/220x300?text=📱';
    
    // Группировка характеристик
    const groups = [
        {
            title: "ძირითადი მახასიათებლები",
            specs: [
                { name: "გამოშვების წელი", value: phone['Год выпуска'] || '-' },
                { name: "ოპერაციული სისტემა", value: phone.ОС || '-' },
                { name: "ოპერაციული სისტემის ვერსია", value: phone['Версия ОС'] || '-' },
                { name: "პროცესორი (CPU)", value: phone.Процессор || '-' },
                { name: "გრაფიკული პროცესორი (GPU)", value: phone['Графический процессор'] || '-' },
                { name: "AnTuTu შეფასება", value: phone['Оценка AnTuTu'] || '-' },
                { name: "Geekbench (მრავალბირთვიანი)", value: phone['Geekbench (многоядерное)'] || '-' }
            ]
        },
        {
            title: "ეკრანი",
            specs: [
                { name: "ეკრანის ზომა (დუიმი)", value: phone['Размер дисплея (дюймы)'] || '-' },
                { name: "გაფართოება", value: phone['Разрешение дисплея'] || '-' },
                { name: "ეკრანის ტიპი", value: phone['Тип дисплея'] || '-' },
                { name: "განახლების სიხშირე (Hz)", value: phone['Частота обновления (Гц)'] || '-' },
                { name: "მაქსიმალური სიკაშკაშე (ნიტი)", value: phone['Пиковая яркость (нит)'] || '-' },
                { name: "HDR მხარდაჭერა", value: phone['Поддержка HDR'] || '-' },
                { name: "დამცავი მინა", value: phone['Защитное стекло'] || '-' },
                { name: "ეკრანი/კორპუსის თანაფარდობა", value: phone['Соотношение экран/корпус'] || '-' },
                { name: "პიქსელების სიმჭიდროვე (PPI)", value: phone['Плотность пикселей (PPI)'] || '-' }
            ]
        },
        {
            title: "პროცესორი",
            specs: [
                { name: "პროცესორი (CPU)", value: phone.Процессор || '-' },
                { name: "CPU არქიტექტურა", value: phone['Архитектура CPU'] || '-' },
                { name: "გრაფიკული პროცესორი (GPU)", value: phone['Графический процессор'] || '-' },
                { name: "GPU არქიტექტურა", value: phone['Архитектура GPU'] || '-' },
                { name: "NPU", value: phone.NPU || '-' },
                { name: "ISP", value: phone.ISP || '-' },
                { name: "მოდემი", value: phone.Модем || '-' },
                { name: "AnTuTu შეფასება", value: phone['Оценка AnTuTu'] || '-' },
                { name: "Geekbench (ერთბირთვიანი)", value: phone['Geekbench (одиночное ядро)'] || '-' },
                { name: "Geekbench (მრავალბირთვიანი)", value: phone['Geekbench (многоядерное)'] || '-' }
            ]
        },
        {
            title: "მეხსიერება",
            specs: [
                { name: "ოპერატიული მეხსიერება (GB)", value: phone['ОЗУ (ГБ)'] || '-' },
                { name: "ოპერატიული მეხსიერების ტიპი", value: phone['Тип ОЗУ'] || '-' },
                { name: "ოპერატიული მეხსიერების სიხშირე (MHz)", value: phone['Частота ОЗУ (МГц)'] || '-' },
                { name: "შიდა მეხსიერება (GB)", value: phone['ПЗУ (ГБ)'] || '-' },
                { name: "შიდა მეხსიერების ტიპი", value: phone['Тип ПЗУ'] || '-' },
                { name: "შიდა მეხსიერების სიჩქარე", value: phone['Скорость ПЗУ'] || '-' }
            ]
        },
        {
            title: "გაგრილების სისტემა",
            specs: [
                { name: "გაგრილების სისტემა", value: phone['Система охлаждения'] || '-' },
                { name: "გაგრილების ზედაპირი (მმ²)", value: phone['Площадь охлаждения (мм²)'] || '-' }
            ]
        },
        {
            title: "კამერა",
            specs: [
                { name: "მთავარი კამერა (MP)", value: phone['Основная камера (Мп)'] || '-' },
                { name: "ულტრა ფართო კუთხის კამერა (MP)", value: phone['Сверхширокоугольная камера (Мп)'] || '-' },
                { name: "ტელე ფოტო 1 (MP)", value: phone['Телефото 1 (Мп)'] || '-' },
                { name: "ტელე ფოტო 2 (MP)", value: phone['Телефото 2 (Мп)'] || '-' },
                { name: "წინა კამერა (MP)", value: phone['Фронтальная камера (Мп)'] || '-' },
                { name: "სენსორის ზომა (მთავარი)", value: phone['Размер сенсора (основной)'] || '-' },
                { name: "პიქსელის ზომა (მთავარი)", value: phone['Размер пикселя (основной)'] || '-' },
                { name: "ზუმის შესაძლებლობები", value: phone['Возможности зума'] || '-' },
                { name: "ვიდეო ჩაწერა", value: phone.Видеозапись || '-' },
                { name: "ნელი მოძრაობა", value: phone['Замедленная съемка'] || '-' },
                { name: "კამერის ფუნქციები", value: phone['Функции камеры'] || '-' }
            ]
        },
        {
            title: "ბატარეა",
            specs: [
                { name: "ტევადობა (mAh)", value: phone['Емкость батареи (mAh)'] || '-' },
                { name: "ბატარეის ტიპი", value: phone['Тип батареи'] || '-' },
                { name: "სწრაფი დატენვა", value: phone['Быстрая зарядка'] || '-' },
                { name: "უსადენო დატენვა", value: phone['Беспроводная зарядка'] || '-' },
                { name: "უკუღმა უსადენო დატენვა", value: phone['Обратная беспроводная зарядка'] || '-' },
                { name: "დატენვის ინტერფეისი", value: phone['Интерфейс зарядки'] || '-' },
                { name: "მუშაობის დრო (საათი)", value: phone['Время работы от батареи (ч)'] || '-' },
                { name: "მოხმარება ლოდინის რეჟიმში", value: phone['Потребление в режиме ожидания'] || '-' },
                { name: "მაქსიმალური სიმძლავრე", value: phone['Пиковая мощность'] || '-' }
            ]
        },
        {
            title: "დიზაინი",
            specs: [
                { name: "წონა (გრ)", value: phone['Вес (г)'] || '-' },
                { name: "ზომები (მმ)", value: phone['Габариты (мм)'] || '-' },
                { name: "კორპუსის მასალა", value: phone['Материал корпуса'] || '-' },
                { name: "წყლისგან დაცვა", value: phone['Защита от воды'] || '-' },
                { name: "მტვრისგან დაცვა", value: phone['Защита от пыли'] || '-' },
                { name: "სერთიფიკატი", value: phone['Сертификат защиты'] || '-' },
                { name: "ჩარჩოს მასალა", value: phone['Материал рамки'] || '-' },
                { name: "უკანა პანელის მასალა", value: phone['Материал задней панели'] || '-' },
                { name: "ფერები", value: phone.Цвета || '-' }
            ]
        },
        {
            title: "კავშირი",
            specs: [
                { name: "5G მხარდაჭერა", value: phone['Поддержка 5G'] || '-' },
                { name: "5G დიაპაზონები", value: phone['Диапазоны 5G'] || '-' },
                { name: "mmWave მხარდაჭერა", value: phone['Поддержка mmWave'] || '-' },
                { name: "SIM სლოტები", value: phone['Слоты SIM'] || '-' },
                { name: "SIM ბარათის ტიპი", value: phone['Тип SIM'] || '-' },
                { name: "Wi-Fi", value: phone['Wi-Fi'] || '-' },
                { name: "Wi-Fi მახასიათებლები", value: phone['Особенности Wi-Fi'] || '-' },
                { name: "Bluetooth", value: phone.Bluetooth || '-' },
                { name: "Bluetooth კოდეკები", value: phone['Кодеки Bluetooth'] || '-' },
                { name: "NFC", value: phone.NFC || '-' },
                { name: "IR პორტი", value: phone['ИК-порт'] || '-' },
                { name: "USB ვერსია", value: phone['Версия USB'] || '-' },
                { name: "GPS", value: phone.GPS || '-' },
                { name: "სატელიტური კავშირი", value: phone['Спутниковая связь'] || '-' }
            ]
        },
        {
            title: "აუდიო",
            specs: [
                { name: "დინამიკები", value: phone.Динамики || '-' },
                { name: "აუდიო კონფიგურაცია", value: phone['Аудионастройка'] || '-' },
                { name: "მიკროფონები", value: phone.Микрофоны || '-' },
                { name: "აუდიო ჯეკი", value: phone.Аудиоразъем || '-' },
                { name: "სივრცული ხმა", value: phone['Пространственный звук'] || '-' }
            ]
        },
        {
            title: "უსაფრთხოება",
            specs: [
                { name: "თითის ანაბეჭდის სკანერი", value: phone['Сканер отпечатков'] || '-' },
                { name: "სახით განბლოკვა", value: phone['Разблокировка по лицу'] || '-' }
            ]
        },
        {
            title: "სენსორები",
            specs: [
                { name: "აქსელერომეტრი", value: phone.Акселерометр || '-' },
                { name: "გიროსკოპი", value: phone.Гироскоп || '-' },
                { name: "სიახლოვის სენსორი", value: phone['Датчик приближения'] || '-' },
                { name: "კომპასი", value: phone.Компас || '-' },
                { name: "ბარომეტრი", value: phone.Барометр || '-' },
                { name: "განათების სენსორი", value: phone['Датчик освещенности'] || '-' },
                { name: "ჰოლის სენსორი", value: phone['Датчик Холла'] || '-' },
                { name: "LiDAR", value: phone.LiDAR || '-' },
                { name: "თერმომეტრი", value: phone.Термометр || '-' },
                { name: "SpO2 სენსორი", value: phone['Датчик SpO2'] || '-' }
            ]
        },
        {
            title: "სხვა ფუნქციები",
            specs: [
                { name: "სტილუსის მხარდაჭერა", value: phone['Поддержка стилуса'] || '-' },
                { name: "სტილუსის ტიპი", value: phone['Тип стилуса'] || '-' },
                { name: "სამუშაო მაგიდის რეჟიმი", value: phone['Режим рабочего стола'] || '-' },
                { name: "VR მხარდაჭერა", value: phone['Поддержка VR'] || '-' },
                { name: "AI ფუნქციები", value: phone['ИИ-функции'] || '-' },
                { name: "თამაშის ფუნქციები", value: phone['Игровые функции'] || '-' },
                { name: "უსაფრთხოების ჩიპი", value: phone['Безопасный чип'] || '-' }
            ]
        },
        {
            title: "კომპლექტაცია",
            specs: [
                { name: "დამტენი კომპლექტში", value: phone['Зарядное устройство в комплекте'] || '-' },
                { name: "კაბელის ტიპი", value: phone['Тип кабеля'] || '-' },
                { name: "ადაპტერი კომპლექტში", value: phone['Адаптер в комплекте'] || '-' },
                { name: "ყურსასმენები კომპლექტში", value: phone['Наушники в комплекте'] || '-' },
                { name: "ქეისი კომპლექტში", value: phone['Чехол в комплекте'] || '-' }
            ]
        },
        {
            title: "ეკოლოგია",
            specs: [
                { name: "გადამუშავებული მასალები", value: phone['Переработанные материалы'] || '-' },
                { name: "შეფუთვა", value: phone.Упаковка || '-' },
                { name: "ეკოსერთიფიკატები", value: phone.Экосертификаты || '-' },
                { name: "რემონტის ინდექსი", value: phone['Индекс ремонтопригодности'] || '-' },
                { name: "ბატარეის ციკლები", value: phone['Циклы батареи'] || '-' },
                { name: "SAR (თავი)", value: phone['SAR (голова)'] || '-' },
                { name: "SAR (სხეული)", value: phone['SAR (тело)'] || '-' }
            ]
        },
        {
            title: "ფასი",
            specs: [
                { name: "საწყისი ფასი (რუბ)", value: phone['Стартовая цена (руб)'] ? 
                    `${parseInt(phone['Стартовая цена (руб)']).toLocaleString('ru-RU')} რუბ.` : '-' },
                { name: "მიმდინარე ფასი (რუბ)", value: phone['Текущая цена (руб)'] ? 
                    `${parseInt(phone['Текущая цена (руб)']).toLocaleString('ru-RU')} რუბ.` : '-' },
                { name: "ხელმისაწვდომობა", value: phone.Доступность || '-' },
                { name: "გარანტია (თვე)", value: phone['Гарантия (мес)'] || '-' }
            ]
        }
    ];
    
    // Генерация HTML с группами
    let specsHTML = '';
    
    groups.forEach(group => {
        // Проверяем, есть ли хотя бы одно значение в группе
        const hasValues = group.specs.some(spec => spec.value && spec.value !== '-');
        
        if (hasValues) {
            specsHTML += `<div class="spec-group">`;
            specsHTML += `<h4 class="group-title">${group.title}</h4>`;
            
            group.specs.forEach(spec => {
                if (spec.value && spec.value !== '-') {
                    specsHTML += `
                        <div class="spec-item">
                            <span class="spec-title">${spec.name}</span>
                            <span class="spec-value">${spec.value}</span>
                        </div>
                    `;
                }
            });
            
            specsHTML += `</div>`;
        }
    });
    
    specsElement.innerHTML = specsHTML;
}

// Функция для отображения спецификаций в мобильном виде
function displayMobileSpecs() {
    const container = document.getElementById('mobile-specs-container');
    container.innerHTML = '';
    
    // Показываем контейнер
    document.getElementById('mobile-specs').style.display = 'block';
    
    // Группы характеристик
    const groups = [
        {
            title: "ძირითადი მახასიათებლები",
            specs: [
                { name: "გამოშვების წელი", key: 'Год выпуска' },
                { name: "ოპერაციული სისტემა", key: 'ОС' },
                { name: "ოპერაციული სისტემის ვერსია", key: 'Версия ОС' },
                { name: "პროცესორი (CPU)", key: 'Процессор' },
                { name: "გრაფიკული პროცესორი (GPU)", key: 'Графический процессор' },
                { name: "AnTuTu შეფასება", key: 'Оценка AnTuTu' },
                { name: "Geekbench (მრავალბირთვიანი)", key: 'Geekbench (многоядерное)' }
            ]
        },
        {
            title: "ეკრანი",
            specs: [
                { name: "ეკრანის ზომა (დუიმი)", key: 'Размер дисплея (дюймы)' },
                { name: "გაფართოება", key: 'Разрешение дисплея' },
                { name: "ეკრანის ტიპი", key: 'Тип дисплея' },
                { name: "განახლების სიხშირე (Hz)", key: 'Частота обновления (Гц)' },
                { name: "მაქსიმალური სიკაშკაშე (ნიტი)", key: 'Пиковая яркость (нит)' },
                { name: "HDR მხარდაჭერა", key: 'Поддержка HDR' },
                { name: "დამცავი მინა", key: 'Защитное стекло' },
                { name: "ეკრანი/კორპუსის თანაფარდობა", key: 'Соотношение экран/корпус' },
                { name: "პიქსელების სიმჭიდროვე (PPI)", key: 'Плотность пикселей (PPI)' }
            ]
        },
        {
            title: "პროცესორი",
            specs: [
                { name: "პროცესორი (CPU)", key: 'Процессор' },
                { name: "CPU არქიტექტურა", key: 'Архитектура CPU' },
                { name: "გრაფიკული პროცესორი (GPU)", key: 'Графический процессор' },
                { name: "GPU არქიტექტურა", key: 'Архитектура GPU' },
                { name: "NPU", key: 'NPU' },
                { name: "ISP", key: 'ISP' },
                { name: "მოდემი", key: 'Модем' },
                { name: "AnTuTu შეფასება", key: 'Оценка AnTuTu' },
                { name: "Geekbench (ერთბირთვიანი)", key: 'Geekbench (одиночное ядро)' },
                { name: "Geekbench (მრავალბირთვიანი)", key: 'Geekbench (многоядерное)' }
            ]
        },
        {
            title: "მეხსიერება",
            specs: [
                { name: "ოპერატიული მეხსიერება (GB)", key: 'ОЗУ (ГБ)' },
                { name: "ოპერატიული მეხსიერების ტიპი", key: 'Тип ОЗУ' },
                { name: "ოპერატიული მეხსიერების სიხშირე (MHz)", key: 'Частота ОЗУ (МГц)' },
                { name: "შიდა მეხსიერება (GB)", key: 'ПЗУ (ГБ)' },
                { name: "შიდა მეხსიერების ტიპი", key: 'Тип ПЗУ' },
                { name: "შიდა მეხსიერების სიჩქარე", key: 'Скорость ПЗУ' }
            ]
        },
        {
            title: "გაგრილების სისტემა",
            specs: [
                { name: "გაგრილების სისტემა", key: 'Система охлаждения' },
                { name: "გაგრილების ზედაპირი (მმ²)", key: 'Площадь охлаждения (мм²)' }
            ]
        },
        {
            title: "კამერა",
            specs: [
                { name: "მთავარი კამერა (MP)", key: 'Основная камера (Мп)' },
                { name: "ულტრა ფართო კუთხის კამერა (MP)", key: 'Сверхширокоугольная камера (Мп)' },
                { name: "ტელე ფოტო 1 (MP)", key: 'Телефото 1 (Мп)' },
                { name: "ტელე ფოტო 2 (MP)", key: 'Телефото 2 (Мп)' },
                { name: "წინა კამერა (MP)", key: 'Фронтальная камера (Мп)' },
                { name: "სენსორის ზომა (მთავარი)", key: 'Размер сенсора (основной)' },
                { name: "პიქსელის ზომა (მთავარი)", key: 'Размер пикселя (основной)' },
                { name: "ზუმის შესაძლებლობები", key: 'Возможности зума' },
                { name: "ვიდეო ჩაწერა", key: 'Видеозапись' },
                { name: "ნელი მოძრაობა", key: 'Замедленная съемка' },
                { name: "კამერის ფუნქციები", key: 'Функции камеры' }
            ]
        },
        {
            title: "ბატარეა",
            specs: [
                { name: "ტევადობა (mAh)", key: 'Емкость батареи (mAh)' },
                { name: "ბატარეის ტიპი", key: 'Тип батареи' },
                { name: "სწრაფი დატენვა", key: 'Быстрая зарядка' },
                { name: "უსადენო დატენვა", key: 'Беспроводная зарядка' },
                { name: "უკუღმა უსადენო დატენვა", key: 'Обратная беспроводная зарядка' },
                { name: "დატენვის ინტერფეისი", key: 'Интерфейс зарядки' },
                { name: "მუშაობის დრო (საათი)", key: 'Время работы от батареи (ч)' },
                { name: "მოხმარება ლოდინის რეჟიმში", key: 'Потребление в режиме ожидания' },
                { name: "მაქსიმალური სიმძლავრე", key: 'Пиковая мощность' }
            ]
        },
        {
            title: "დიზაინი",
            specs: [
                { name: "წონა (გრ)", key: 'Вес (г)' },
                { name: "ზომები (მმ)", key: 'Габариты (мм)' },
                { name: "კორპუსის მასალა", key: 'Материал корпуса' },
                { name: "წყლისგან დაცვა", key: 'Защита от воды' },
                { name: "მტვრისგან დაცვა", key: 'Защита от пыли' },
                { name: "სერთიფიკატი", key: 'Сертификат защиты' },
                { name: "ჩარჩოს მასალა", key: 'Материал рамки' },
                { name: "უკანა პანელის მასალა", key: 'Материал задней панели' },
                { name: "ფერები", key: 'Цвета' }
            ]
        },
        {
            title: "კავშირი",
            specs: [
                { name: "5G მხარდაჭერა", key: 'Поддержка 5G' },
                { name: "5G დიაპაზონები", key: 'Диапазоны 5G' },
                { name: "mmWave მხარდაჭერა", key: 'Поддержка mmWave' },
                { name: "SIM სლოტები", key: 'Слоты SIM' },
                { name: "SIM ბარათის ტიპი", key: 'Тип SIM' },
                { name: "Wi-Fi", key: 'Wi-Fi' },
                { name: "Wi-Fi მახასიათებლები", key: 'Особенности Wi-Fi' },
                { name: "Bluetooth", key: 'Bluetooth' },
                { name: "Bluetooth კოდეკები", key: 'Кодеки Bluetooth' },
                { name: "NFC", key: 'NFC' },
                { name: "IR პორტი", key: 'ИК-порт' },
                { name: "USB ვერსია", key: 'Версия USB' },
                { name: "GPS", key: 'GPS' },
                { name: "სატელიტური კავშირი", key: 'Спутниковая связь' }
            ]
        },
        {
            title: "აუდიო",
            specs: [
                { name: "დინამიკები", key: 'Динамики' },
                { name: "აუდიო კონფიგურაცია", key: 'Аудионастройка' },
                { name: "მიკროფონები", key: 'Микрофоны' },
                { name: "აუდიო ჯეკი", key: 'Аудиоразъем' },
                { name: "სივრცული ხმა", key: 'Пространственный звук' }
            ]
        },
        {
            title: "უსაფრთხოება",
            specs: [
                { name: "თითის ანაბეჭდის სკანერი", key: 'Сканер отпечатков' },
                { name: "სახით განბლოკვა", key: 'Разблокировка по лицу' }
            ]
        },
        {
            title: "სენსორები",
            specs: [
                { name: "აქსელერომეტრი", key: 'Акселерометр' },
                { name: "გიროსკოპი", key: 'Гироскоп' },
                { name: "სიახლოვის სენსორი", key: 'Датчик приближения' },
                { name: "კომპასი", key: 'Компас' },
                { name: "ბარომეტრი", key: 'Барометр' },
                { name: "განათების სენსორი", key: 'Датчик освещенности' },
                { name: "ჰოლის სენსორი", key: 'Датчик Холла' },
                { name: "LiDAR", key: 'LiDAR' },
                { name: "თერმომეტრი", key: 'Термометр' },
                { name: "SpO2 სენსორი", key: 'Датчик SpO2' }
            ]
        },
        {
            title: "სხვა ფუნქციები",
            specs: [
                { name: "სტილუსის მხარდაჭერა", key: 'Поддержка стилуса' },
                { name: "სტილუსის ტიპი", key: 'Тип стилуса' },
                { name: "სამუშაო მაგიდის რეჟიმი", key: 'Режим рабочего стола' },
                { name: "VR მხარდაჭერა", key: 'Поддержка VR' },
                { name: "AI ფუნქციები", key: 'ИИ-функции' },
                { name: "თამაშის ფუნქციები", key: 'Игровые функции' },
                { name: "უსაფრთხოების ჩიპი", key: 'Безопасный чип' }
            ]
        },
        {
            title: "კომპლექტაცია",
            specs: [
                { name: "დამტენი კომპლექტში", key: 'Зарядное устройство в комплекте' },
                { name: "კაბელის ტიპი", key: 'Тип кабеля' },
                { name: "ადაპტერი კომპლექტში", key: 'Адаптер в комплекте' },
                { name: "ყურსასმენები კომპლექტში", key: 'Наушники в комплекте' },
                { name: "ქეისი კომპლექტში", key: 'Чехол в комплекте' }
            ]
        },
        {
            title: "ეკოლოგია",
            specs: [
                { name: "გადამუშავებული მასალები", key: 'Переработанные материалы' },
                { name: "შეფუთვა", key: 'Упаковка' },
                { name: "ეკოსერთიფიკატები", key: 'Экосертификаты' },
                { name: "რემონტის ინდექსი", key: 'Индекс ремонтопригодности' },
                { name: "ბატარეის ციკლები", key: 'Циклы батареи' },
                { name: "SAR (თავი)", key: 'SAR (голова)' },
                { name: "SAR (სხეული)", key: 'SAR (тело)' }
            ]
        },
        {
            title: "ფასი",
            specs: [
                { name: "საწყისი ფასი (რუბ)", key: 'Стартовая цена (руб)' },
                { name: "მიმდინარე ფასი (რუბ)", key: 'Текущая цена (руб)' },
                { name: "ხელმისაწვდომობა", key: 'Доступность' },
                { name: "გარანტია (თვე)", key: 'Гарантия (мес)' }
            ]
        }
    ];
    
    let specsHTML = '';
    
    groups.forEach(group => {
        // Проверяем, есть ли хотя бы одно значение в группе
        const hasValues = group.specs.some(spec => 
            (phone1[spec.key] && phone1[spec.key] !== '-') || 
            (phone2[spec.key] && phone2[spec.key] !== '-')
        );
        
        if (hasValues) {
            specsHTML += `<div class="spec-group-mobile">`;
            specsHTML += `<h4 class="group-title-mobile">${group.title}</h4>`;
            
            group.specs.forEach(spec => {
                let value1 = phone1[spec.key] || '-';
                let value2 = phone2[spec.key] || '-';
                
                // Форматируем цену
                if ((spec.key === 'Стартовая цена (руб)' || spec.key === 'Текущая цена (руб)') && value1 !== '-') {
                    value1 = `${parseInt(value1).toLocaleString('ru-RU')} რუბ.`;
                }
                if ((spec.key === 'Стартовая цена (руб)' || spec.key === 'Текущая цена (руб)') && value2 !== '-') {
                    value2 = `${parseInt(value2).toLocaleString('ru-RU')} რუბ.`;
                }
                
                if (value1 !== '-' || value2 !== '-') {
                    specsHTML += `
                        <div class="spec-item-mobile">
                            <div class="spec-name-mobile">${spec.name}</div>
                            <div class="spec-value-container">
                                <div class="spec-phone">
                                    <div class="spec-phone-title">${phone1.Бренд}</div>
                                    <div class="spec-value-mobile">${value1}</div>
                                </div>
                                <div class="spec-phone">
                                    <div class="spec-phone-title">${phone2.Бренд}</div>
                                    <div class="spec-value-mobile">${value2}</div>
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
            
            specsHTML += `</div>`;
        }
    });
    
    container.innerHTML = specsHTML;
}

// Сравнение характеристик телефонов
function comparePhonesHandler() {
    if (!phone1 || !phone2) {
        alert('აირჩიეთ ორივე ტელეფონი შესადარებლად');
        return;
    }
    
    // Показываем секцию с результатами
    resultsSection.style.display = 'block';
    
    // Обновляем заголовки
    document.getElementById('phone1-title').textContent = 
        `${phone1.Бренд} ${phone1.Модель}`;
        
    document.getElementById('phone2-title').textContent = 
        `${phone2.Бренд} ${phone2.Модель}`;
        
    document.getElementById('phone1-title-score').textContent = 
        `${phone1.Бренд} ${phone1.Модель}`;
        
    document.getElementById('phone2-title-score').textContent = 
        `${phone2.Бренд} ${phone2.Модель}`;
    
    // Сравниваем телефоны
    const comparisonResult = comparePhones(phone1, phone2);
    
    // Отображаем результаты балльной системы
    displayComparisonResult(comparisonResult);
    
    // Отображаем таблицу характеристик
    displayComparisonTable(comparisonResult);
    
    // Для мобильных: показываем спецификации в новом формате
    if (window.innerWidth <= 768) {
        displayMobileSpecs();
    }
    
    // Прокрутка к результатам
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Отображение таблицы характеристик
function displayComparisonTable(result) {
    // Обновляем заголовки таблицы
    document.getElementById('phone1-table-title').textContent = 
        `${phone1.Бренд} ${phone1.Модель}`;
        
    document.getElementById('phone2-table-title').textContent = 
        `${phone2.Бренд} ${phone2.Модель}`;
    
    // Список характеристик для сравнения
    const specsToCompare = [
        'Год выпуска', 'ОС', 'Версия ОС', 
        'Размер дисплея (дюймы)', 'Разрешение дисплея', 'Тип дисплея',
        'Частота обновления (Гц)', 'Пиковая яркость (нит)', 'Поддержка HDR',
        'Защитное стекло', 'Соотношение экран/корпус', 'Плотность пикселей (PPI)',
        'Процессор', 'Архитектура CPU', 'Графический процессор', 'Архитектура GPU',
        'NPU', 'ISP', 'Модем', 'Оценка AnTuTu', 'Geekbench (одиночное ядро)', 
        'Geekbench (многоядерное)', 'ОЗУ (ГБ)', 'Тип ОЗУ', 'Частота ОЗУ (МГц)',
        'ПЗУ (ГБ)', 'Тип ПЗУ', 'Скорость ПЗУ', 'Система охлаждения', 'Площадь охлаждения (мм²)',
        'Основная камера (Мп)', 'Сверхширокоугольная камера (Мп)', 'Телефото 1 (Мп)',
        'Телефото 2 (Мп)', 'Фронтальная камера (Мп)', 'Размер сенсора (основной)',
        'Размер пикселя (основной)', 'Возможности зума', 'Видеозапись', 'Замедленная съемка',
        'Функции камеры', 'Емкость батареи (mAh)', 'Тип батареи', 'Быстрая зарядка',
        'Беспроводная зарядка', 'Обратная беспроводная зарядка', 'Интерфейс зарядки',
        'Время работы от батареи (ч)', 'Потребление в режиме ожидания', 'Пиковая мощность',
        'Вес (г)', 'Габариты (мм)', 'Материал корпуса', 'Защита от воды', 'Защита от пыли',
        'Сертификат защиты', 'Материал рамки', 'Материал задней панели', 'Цвета',
        'Поддержка 5G', 'Диапазоны 5G', 'Поддержка mmWave', 'Слоты SIM', 'Тип SIM',
        'Wi-Fi', 'Особенности Wi-Fi', 'Bluetooth', 'Кодеки Bluetooth', 'NFC', 'ИК-порт',
        'Версия USB', 'GPS', 'Спутниковая связь', 'Динамики', 'Аудионастройка', 'Микрофоны',
        'Аудиоразъем', 'Пространственный звук', 'Сканер отпечатков', 'Разблокировка по лицу',
        'Акселерометр', 'Гироскоп', 'Датчик приближения', 'Компас', 'Барометр',
        'Датчик освещенности', 'Датчик Холла', 'LiDAR', 'Термометр', 'Датчик SpO2',
        'Поддержка стилуса', 'Тип стилуса', 'Режим рабочего стола', 'Поддержка VR',
        'ИИ-функции', 'Игровые функции', 'Безопасный чип', 'Зарядное устройство в комплекте',
        'Тип кабеля', 'Адаптер в комплекте', 'Наушники в комплекте', 'Чехол в комплекте',
        'Переработанные материалы', 'Упаковка', 'Экосертификаты', 'Индекс ремонтопригодности',
        'Циклы батареи', 'SAR (голова)', 'SAR (тело)', 'Стартовая цена (руб)', 'Текущая цена (руб)',
        'Доступность', 'Гарантия (мес)'
    ];
    
    // Строим таблицу сравнения
    const comparisonBody = document.getElementById('comparison-body');
    comparisonBody.innerHTML = '';
    
    specsToCompare.forEach(spec => {
        let value1 = phone1[spec] || '-';
        let value2 = phone2[spec] || '-';
        
        // Форматируем цену
        if ((spec === 'Стартовая цена (руб)' || spec === 'Текущая цена (руб)') && value1 !== '-') {
            value1 = `${parseInt(value1).toLocaleString('ru-RU')} რუბ.`;
        }
        if ((spec === 'Стартовая цена (руб)' || spec === 'Текущая цена (руб)') && value2 !== '-') {
            value2 = `${parseInt(value2).toLocaleString('ru-RU')} რუბ.`;
        }
        
        const row = document.createElement('tr');
        
        // Выделяем лучшие значения
        let highlight1 = '';
        let highlight2 = '';
        
        // Используем логику сравнения
        const comparison = compareFeature(spec, value1, value2);
        if (comparison === 1) highlight1 = 'highlight';
        else if (comparison === 2) highlight2 = 'highlight';
        
        row.innerHTML = `
            <td><strong>${spec}</strong></td>
            <td class="${highlight1}">${value1}</td>
            <td class="${highlight2}">${value2}</td>
        `;
        
        comparisonBody.appendChild(row);
    });
}

// Функция для сравнения характеристик
function compareFeature(spec, value1, value2) {
    // Если значения равны, нет победителя
    if (value1 === value2) return 0;
    
    // Для числовых характеристик
    if (!isNaN(parseFloat(value1)) {
        return parseFloat(value1) > parseFloat(value2) ? 1 : 2;
    }
    
    // Для текстовых характеристик
    return value1 > value2 ? 1 : 2;
}

// Функция для отображения результатов сравнения
function displayComparisonResult(result) {
    const resultSection = document.getElementById('comparison-result');
    resultSection.style.display = 'block';
    
    // Отображаем общие баллы
    document.getElementById('phone1-score').textContent = 
        result.phone1.score.total;
        
    document.getElementById('phone2-score').textContent = 
        result.phone2.score.total;
    
    // Добавляем классы победителя/проигравшего
    const scoreCard1 = document.getElementById('score-card1');
    const scoreCard2 = document.getElementById('score-card2');
    
    // Удаляем предыдущие классы
    scoreCard1.classList.remove('winner', 'loser');
    scoreCard2.classList.remove('winner', 'loser');
    
    if (result.winner) {
        if (result.winner.phone === phone1) {
            scoreCard1.classList.add('winner');
            scoreCard2.classList.add('loser');
            
            document.getElementById('winner-name').textContent = 
                `${phone1.Бренд} ${phone1.Модель}`;
            document.getElementById('winner-diff').textContent = 
                result.winner.difference;
                
            document.getElementById('winner-banner').style.display = 'block';
            document.getElementById('draw-banner').style.display = 'none';
        } else {
            scoreCard1.classList.add('loser');
            scoreCard2.classList.add('winner');
            
            document.getElementById('winner-name').textContent = 
                `${phone2.Бренд} ${phone2.Модель}`;
            document.getElementById('winner-diff').textContent = 
                result.winner.difference;
                
            document.getElementById('winner-banner').style.display = 'block';
            document.getElementById('draw-banner').style.display = 'none';
        }
    } else {
        scoreCard1.classList.remove('winner', 'loser');
        scoreCard2.classList.remove('winner', 'loser');
        
        document.getElementById('winner-banner').style.display = 'none';
        document.getElementById('draw-banner').style.display = 'block';
    }
    
    // Отображаем детализированные баллы
    const categories = {
        'პროდუქტიულობა': 'performance',
        'კამერა': 'camera',
        'ბატარეა': 'battery',
        'ეკრანი': 'display',
        'კავშირი': 'connectivity',
        'ფუნქციები': 'features'
    };
    
    let categoriesHTML = '';
    
    for (const [name, key] of Object.entries(categories)) {
        const score1 = result.phone1.score.categories[key];
        const score2 = result.phone2.score.categories[key];
        
        // Рассчитываем процент для отображения
        const maxScore = Math.max(score1, score2, 1);
        const percent1 = (score1 / maxScore) * 100;
        const percent2 = (score2 / maxScore) * 100;
        
        // Определяем цвет для первого телефона
        let color1 = '#3498db'; // Синий
        if (score1 > score2) color1 = '#27ae60'; // Зеленый
        else if (score1 < score2) color1 = '#e74c3c'; // Красный
        
        // Определяем цвет для второго телефона
        let color2 = '#3498db'; // Синий
        if (score2 > score1) color2 = '#27ae60'; // Зеленый
        else if (score2 < score1) color2 = '#e74c3c'; // Красный
        
        categoriesHTML += `
            <div class="category">
                <div class="category-title">${name}</div>
                <div class="phone-score">
                    <span>${phone1.Бренд}</span>
                    <span>${score1.toFixed(1)}</span>
                </div>
                <div class="category-bar">
                    <div class="category-fill" 
                         style="width: ${percent1}%; background: ${color1};"></div>
                </div>
                
                <div class="phone-score">
                    <span>${phone2.Бренд}</span>
                    <span>${score2.toFixed(1)}</span>
                </div>
                <div class="category-bar">
                    <div class="category-fill" 
                         style="width: ${percent2}%; background: ${color2};"></div>
                </div>
            </div>
        `;
    }
    
    document.getElementById('category-scores').innerHTML = categoriesHTML;
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Обработчик клика вне области поиска
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-input-container')) {
            phone1Results.style.display = 'none';
            phone2Results.style.display = 'none';
        }
    });
});

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
