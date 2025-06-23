// Функция для создания карусели
function initCarousel() {
    const carouselContainer = document.getElementById('customCarousel');
    if (!carouselContainer) return;

    // Конфигурация карусели (может загружаться из админки)
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
            // Заглушка с логотипом
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
        
        // Обновляем активный класс
        slides.forEach((slide, i) => {
            slide.style.transform = `translateX(${100 * (i - index)}%)`;
            slide.classList.toggle('active', i === index);
        });
        
        indicators.forEach((indicator, i) => {
            indicator.classList.toggle('active', i === index);
        });
        
        currentIndex = index;
    }

    // Автоматическая смена слайдов
    function startAutoSlide() {
        autoSlideInterval = setInterval(() => {
            showSlide(currentIndex + 1);
        }, carouselConfig.speed);
    }

    // Обработчики событий
    prevBtn.addEventListener('click', () => {
        clearInterval(autoSlideInterval);
        showSlide(currentIndex - 1);
        startAutoSlide();
    });

    nextBtn.addEventListener('click', () => {
        clearInterval(autoSlideInterval);
        showSlide(currentIndex + 1);
        startAutoSlide();
    });

    indicatorsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('carousel-indicator')) {
            clearInterval(autoSlideInterval);
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
            // Проверяем, является ли файл изображением
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
                // Рассчитываем новые размеры
                let width = img.width;
                let height = img.height;
                
                if (width > maxWidth) {
                    height = (maxWidth / width) * height;
                    width = maxWidth;
                }

                // Создаем canvas для сжатия
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                
                // Конвертируем в blob
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
