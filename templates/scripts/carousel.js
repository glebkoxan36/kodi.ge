// Добавляем стили для карусели и анимации
const carouselStyles = document.createElement('style');
carouselStyles.textContent = `
/* Стили для кастомной карусели */
.custom-carousel {
    position: relative;
    width: 100%;
    height: 400px;
    overflow: hidden;
    border-radius: 15px;
    margin: 30px 0;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(0, 198, 255, 0.3);
}

.carousel-inner {
    display: flex;
    height: 100%;
    transition: transform 0.6s ease;
}

.carousel-slide {
    min-width: 100%;
    height: 100%;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}

.carousel-slide img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    position: absolute;
    top: 0;
    left: 0;
    z-index: 1;
}

.carousel-content {
    position: relative;
    z-index: 2;
    text-align: center;
    color: white;
    padding: 30px;
    max-width: 800px;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.7);
    background: rgba(13, 21, 37, 0.7);
    border-radius: 15px;
    backdrop-filter: blur(5px);
}

.carousel-content h3 {
    font-size: 2.2rem;
    margin-bottom: 15px;
    color: var(--accent-color);
}

.carousel-content p {
    font-size: 1.2rem;
    line-height: 1.6;
}

.carousel-control {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(0, 0, 0, 0.5);
    border: none;
    color: white;
    font-size: 2rem;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 10;
    transition: all 0.3s ease;
    opacity: 0.7;
}

.carousel-control:hover {
    opacity: 1;
    background: rgba(0, 198, 255, 0.5);
}

.carousel-control.prev {
    left: 20px;
}

.carousel-control.next {
    right: 20px;
}

.carousel-indicators {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 10px;
    z-index: 10;
}

.carousel-indicator {
    width: 15px;
    height: 15px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.5);
    cursor: pointer;
    transition: all 0.3s ease;
}

.carousel-indicator.active {
    background: var(--accent-color);
    transform: scale(1.2);
}

.carousel-logo-placeholder {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(13, 21, 37, 0.9);
    z-index: 2;
}

.carousel-placeholder-text {
    font-size: 1.8rem;
    font-weight: bold;
    margin-top: 30px;
    color: var(--accent-color);
    text-align: center;
    max-width: 80%;
}

/* Анимация для логотипа и колец */
.logo-animated {
    position: relative;
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.logo-ring {
    position: absolute;
    border-radius: 50%;
    border: 2px solid;
    opacity: 0.4;
    animation: float 15s infinite linear;
}

.logo-ring:nth-child(1) {
    width: 100%;
    height: 100%;
    border-color: var(--accent-color);
    animation-duration: 20s;
}

.logo-ring:nth-child(2) {
    width: 80%;
    height: 80%;
    border-color: #ff6b6b;
    animation-duration: 25s;
    animation-direction: reverse;
}

.logo-ring:nth-child(3) {
    width: 60%;
    height: 60%;
    border-color: #4ecdc4;
    animation-duration: 30s;
}

.logo-core {
    position: relative;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 3;
}

.logo-letter {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--primary-color);
}

@keyframes float {
    0% {
        transform: translate(0, 0) rotate(0deg);
    }
    25% {
        transform: translate(5px, -5px) rotate(90deg);
    }
    50% {
        transform: translate(10px, 5px) rotate(180deg);
    }
    75% {
        transform: translate(-5px, 10px) rotate(270deg);
    }
    100% {
        transform: translate(0, 0) rotate(360deg);
    }
}

/* Адаптивность */
@media (max-width: 768px) {
    .custom-carousel {
        height: 300px;
    }
    
    .carousel-content {
        padding: 20px;
    }
    
    .carousel-content h3 {
        font-size: 1.5rem;
    }
    
    .carousel-content p {
        font-size: 1rem;
    }
    
    .carousel-control {
        width: 50px;
        height: 50px;
        font-size: 1.5rem;
    }
}

@media (max-width: 576px) {
    .custom-carousel {
        height: 250px;
    }
    
    .carousel-content {
        padding: 15px;
    }
    
    .carousel-content h3 {
        font-size: 1.3rem;
    }
    
    .carousel-placeholder-text {
        font-size: 1.4rem;
    }
    
    .logo-animated {
        width: 80px;
        height: 80px;
    }
    
    .logo-core {
        width: 30px;
        height: 30px;
    }
    
    .logo-letter {
        font-size: 1.2rem;
    }
}
`;
document.head.appendChild(carouselStyles);

// Функция для создания карусели
function initCarousel() {
    const carouselContainer = document.getElementById('customCarousel');
    if (!carouselContainer) return;

    // Конфигурация карусели
    const carouselConfig = {
        slides: [
            { 
                image: "", 
                title: "აქ იქნება თქვენი რეკლამა", 
                description: "დეტალური ინფორმაცია თქვენი რეკლამის შესახებ" 
            },
            { 
                image: "", 
                title: "სპეციალური შეთავაზება", 
                description: "შეძენის შემთხვევაში მიიღეთ 10% ფასდაკლება" 
            },
            { 
                image: "", 
                title: "ახალი ფუნქციები", 
                description: "გამოიყენეთ ჩვენი ახალი შედარების ინსტრუმენტი" 
            }
        ],
        speed: 5000, // Интервал смены слайдов в мс
        transition: 600  // Длительность анимации в мс
    };

    const inner = carouselContainer.querySelector('.carousel-inner');
    const indicatorsContainer = carouselContainer.querySelector('.carousel-indicators');
    const prevBtn = carouselContainer.querySelector('.carousel-control.prev');
    const nextBtn = carouselContainer.querySelector('.carousel-control.next');

    // Очищаем карусель перед инициализацией
    inner.innerHTML = '';
    indicatorsContainer.innerHTML = '';

    let currentIndex = 0;
    let autoSlideInterval;

    // Создаем слайды
    carouselConfig.slides.forEach((slide, index) => {
        const slideElement = document.createElement('div');
        slideElement.className = 'carousel-slide';
        
        if (slide.image) {
            const img = document.createElement('img');
            img.src = slide.image;
            img.alt = slide.title;
            slideElement.appendChild(img);
        } else {
            // Заглушка с анимированным логотипом
            const placeholder = document.createElement('div');
            placeholder.className = 'carousel-logo-placeholder';
            placeholder.innerHTML = `
                <div class="logo-animated">
                    <div class="logo-ring"></div>
                    <div class="logo-ring"></div>
                    <div class="logo-ring"></div>
                    <div class="logo-core">
                        <div class="logo-letter">K</div>
                    </div>
                </div>
                <div class="carousel-placeholder-text">${slide.title}</div>
            `;
            slideElement.appendChild(placeholder);
        }

        // Контент слайда
        const content = document.createElement('div');
        content.className = 'carousel-content';
        content.innerHTML = `
            <h3>${slide.title}</h3>
            <p>${slide.description}</p>
        `;
        slideElement.appendChild(content);
        
        inner.appendChild(slideElement);

        // Индикаторы
        const indicator = document.createElement('div');
        indicator.className = 'carousel-indicator';
        indicator.dataset.index = index;
        indicatorsContainer.appendChild(indicator);
    });

    // Функция для показа слайда
    function showSlide(index) {
        const slides = inner.querySelectorAll('.carousel-slide');
        const indicators = indicatorsContainer.querySelectorAll('.carousel-indicator');
        
        if (index >= slides.length) index = 0;
        if (index < 0) index = slides.length - 1;
        
        // Обновляем позиции слайдов
        inner.style.transform = `translateX(-${index * 100}%)`;
        
        // Обновляем активный индикатор
        indicators.forEach((indicator, i) => {
            indicator.classList.toggle('active', i === index);
        });
        
        currentIndex = index;
    }

    // Автоматическая смена слайдов
    function startAutoSlide() {
        if (autoSlideInterval) clearInterval(autoSlideInterval);
        autoSlideInterval = setInterval(() => {
            showSlide(currentIndex + 1);
        }, carouselConfig.speed);
    }

    // Обработчики событий
    prevBtn.addEventListener('click', () => {
        showSlide(currentIndex - 1);
        startAutoSlide();
    });

    nextBtn.addEventListener('click', () => {
        showSlide(currentIndex + 1);
        startAutoSlide();
    });

    indicatorsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('carousel-indicator')) {
            showSlide(parseInt(e.target.dataset.index));
            startAutoSlide();
        }
    });

    // Инициализация карусели
    inner.style.transition = `transform ${carouselConfig.transition}ms ease`;
    showSlide(0);
    startAutoSlide();

    // Функция для сжатия изображений
    window.compressImage = function(file, maxWidth = 1200, quality = 0.8) {
        return new Promise((resolve, reject) => {
            if (!file.type.match('image.*')) {
                reject(new Error('File is not an image'));
                return;
            }

            const img = new Image();
            const reader = new FileReader();

            reader.onload = function(e) {
                img.src = e.target.result;
            };

            reader.onerror = reject;

            img.onload = function() {
                let width = img.width;
                let height = img.height;
                
                if (width > maxWidth) {
                    height = (maxWidth / width) * height;
                    width = maxWidth;
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                
                canvas.toBlob(
                    blob => {
                        if (!blob) {
                            reject(new Error('Canvas toBlob failed'));
                            return;
                        }
                        resolve(new File([blob], file.name, {
                            type: 'image/jpeg',
                            lastModified: Date.now()
                        }));
                    },
                    'image/jpeg',
                    quality
                );
            };

            img.onerror = reject;
            reader.readAsDataURL(file);
        });
    };

    // Функция для загрузки изображений в карусель
    window.uploadCarouselImage = async function(fileInput) {
        if (!fileInput.files.length) return;
        
        const file = fileInput.files[0];
        const uploadPath = 'static/img/carousel/';
        
        try {
            // Создаем папку если нужно
            await fetch('/create-carousel-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: uploadPath })
            });
            
            // Сжимаем изображение
            const compressedFile = await compressImage(file);
            
            // Формируем FormData для отправки
            const formData = new FormData();
            formData.append('carouselImage', compressedFile);
            
            // Отправляем на сервер
            const response = await fetch('/upload-carousel-image', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Изображение успешно загружено!');
                // Обновляем карусель
                const newSlide = {
                    image: result.filePath,
                    title: "Новый слайд",
                    description: "Описание нового слайда"
                };
                carouselConfig.slides.push(newSlide);
                initCarousel(); // Переинициализируем карусель
            } else {
                throw new Error(result.error || 'Ошибка загрузки');
            }
        } catch (error) {
            console.error('Ошибка загрузки:', error);
            alert('Ошибка при загрузке изображения: ' + error.message);
        }
    };
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', initCarousel);
