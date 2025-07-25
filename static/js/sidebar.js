document.addEventListener('DOMContentLoaded', function() {
    const sidebarHTML = `
        <div class="sidebar">
            <style>
                .sidebar {
                    width: 220px;
                    height: 100vh;
                    background: linear-gradient(135deg, #2c3e50, #1a1a2e);
                    color: white;
                    position: fixed;
                    left: 0;
                    top: 0;
                    z-index: 100;
                    box-shadow: 3px 0 15px rgba(0,0,0,0.4);
                    overflow-y: auto;
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.1);
                    transform: translateX(0);
                }
                
                .sidebar:hover {
                    box-shadow: 3px 0 20px rgba(0,0,0,0.6);
                }
                
                .nav {
                    padding: 20px 0;
                }
                
                .nav-item {
                    position: relative;
                    overflow: hidden;
                }
                
                .nav-link {
                    color: #ecf0f1 !important;
                    padding: 12px 20px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    transition: all 0.3s ease;
                    position: relative;
                    z-index: 2;
                }
                
                .nav-link:hover {
                    background: rgba(255,255,255,0.1);
                    padding-left: 25px;
                }
                
                .nav-link.active {
                    background: #e74c3c;
                    font-weight: bold;
                }
                
                .nav-link i {
                    width: 24px;
                    text-align: center;
                    transition: transform 0.3s ease;
                }
                
                .submenu {
                    background: rgba(0,0,0,0.2);
                    padding: 0;
                    max-height: 0;
                    overflow: hidden;
                    transition: max-height 0.4s ease-out;
                }
                
                .show {
                    max-height: 1000px;
                    transition: max-height 0.6s ease-in;
                }
                
                .submenu .nav-link {
                    padding: 10px 20px 10px 50px;
                    font-size: 0.9em;
                    opacity: 0.9;
                }
                
                .submenu .nav-link:hover {
                    background: rgba(255,255,255,0.05);
                    padding-left: 55px;
                }
                
                .rotate-icon {
                    transform: rotate(180deg);
                }
                
                .nav-link .fa-chevron-down {
                    margin-left: auto;
                    transition: transform 0.4s cubic-bezier(0.68, -0.55, 0.27, 1.55);
                }
                
                .nav-item::after {
                    content: '';
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 1px;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                .nav-item {
                    animation: fadeIn 0.5s ease-out forwards;
                    opacity: 0;
                }
                
                .nav-item:nth-child(1) { animation-delay: 0.1s; }
                .nav-item:nth-child(2) { animation-delay: 0.2s; }
                .nav-item:nth-child(3) { animation-delay: 0.3s; }
                .nav-item:nth-child(4) { animation-delay: 0.4s; }
                .nav-item:nth-child(5) { animation-delay: 0.5s; }
                .nav-item:nth-child(6) { animation-delay: 0.6s; }
                .nav-item:nth-child(7) { animation-delay: 0.7s; }
                .nav-item:nth-child(8) { animation-delay: 0.8s; }
                .nav-item:nth-child(9) { animation-delay: 0.9s; }
                .nav-item:nth-child(10) { animation-delay: 1.0s; }
            </style>
            
            <ul class="nav flex-column">
                <!-- მთავარი გვერდი -->
                <li class="nav-item">
                    <a class="nav-link active" href="/">
                        <i class="fas fa-home"></i>
                        <span>მთავარი</span>
                    </a>
                </li>
                
                <!-- Apple -->
                <li class="nav-item">
                    <a class="nav-link apple-toggle" href="#">
                        <i class="fab fa-apple"></i>
                        <span>Apple</span>
                        <i class="fas fa-chevron-down"></i>
                    </a>
                    <div class="submenu" id="appleSubmenu">
                        <a class="nav-link" href="#">
                            <span>FMI iCloud</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>SIM ლოკი</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>შავი სია</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>MDM ბლოკი</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>პრემიუმ შემოწმება</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>MacBook</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>სხვა სერვისები</span>
                        </a>
                    </div>
                </li>
                
                <!-- Android -->
                <li class="nav-item">
                    <a class="nav-link android-toggle" href="#">
                        <i class="fab fa-android"></i>
                        <span>Android</span>
                        <i class="fas fa-chevron-down"></i>
                    </a>
                    <div class="submenu" id="androidSubmenu">
                        <a class="nav-link" href="#">
                            <span>Samsung</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>Xiaomi</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>Pixel</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>Huawei</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>Oppo</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>LG</span>
                        </a>
                        <a class="nav-link" href="#">
                            <span>სხვა</span>
                        </a>
                    </div>
                </li>
                
                <!-- სხვა მენიუს პუნქტები -->
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-unlock"></i>
                        <span>განბლოკვა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-exchange-alt"></i>
                        <span>შედარება</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-book"></i>
                        <span>ცოდნის ბაზა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-address-book"></i>
                        <span>კონტაქტები</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-file-contract"></i>
                        <span>პოლიტიკა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-robot"></i>
                        <span>AI რემონტერი</span>
                    </a>
                </li>
            </ul>
        </div>
    `;

    // Вставляем сайдбар в контейнер
    const sidebarContainer = document.getElementById('sidebar-container');
    if (sidebarContainer) {
        sidebarContainer.innerHTML = sidebarHTML;
        
        // Добавляем обработчики событий после создания DOM
        setupSidebar();
    }

    function setupSidebar() {
        // Функция для переключения подменю
        const toggleSubmenu = (buttonClass, menuId) => {
            const button = document.querySelector(buttonClass);
            const menu = document.getElementById(menuId);
            const icon = button.querySelector('.fa-chevron-down');
            
            if (button && menu) {
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    
                    // Закрываем все другие подменю
                    document.querySelectorAll('.submenu').forEach(sub => {
                        if (sub !== menu && sub.classList.contains('show')) {
                            sub.classList.remove('show');
                            const otherIcon = sub.closest('.nav-item').querySelector('.fa-chevron-down');
                            if (otherIcon) otherIcon.classList.remove('rotate-icon');
                        }
                    });
                    
                    // Переключаем текущее подменю
                    menu.classList.toggle('show');
                    icon.classList.toggle('rotate-icon');
                    
                    // Анимация иконки
                    if (icon.classList.contains('rotate-icon')) {
                        icon.style.transform = 'rotate(180deg)';
                    } else {
                        icon.style.transform = 'rotate(0deg)';
                    }
                });
            }
        };

        // Инициализация подменю
        toggleSubmenu('.apple-toggle', 'appleSubmenu');
        toggleSubmenu('.android-toggle', 'androidSubmenu');

        // Анимация при наведении на пункты меню
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('mouseenter', () => {
                link.style.transform = 'translateX(5px)';
            });
            
            link.addEventListener('mouseleave', () => {
                link.style.transform = 'translateX(0)';
            });
        });
        
        // Закрытие подменю при клике вне сайдбара
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.sidebar')) {
                document.querySelectorAll('.submenu').forEach(menu => {
                    menu.classList.remove('show');
                });
                document.querySelectorAll('.fa-chevron-down').forEach(icon => {
                    icon.classList.remove('rotate-icon');
                    icon.style.transform = 'rotate(0deg)';
                });
            }
        });
    }
});
