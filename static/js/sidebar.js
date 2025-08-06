// sidebar.js

document.addEventListener('DOMContentLoaded', function() {
    // Добавляем глобальные стили для адаптивности
    const globalStyles = document.createElement('style');
    globalStyles.textContent = `
        /* Основной контент */
        .main-content {
            transition: margin-left 0.4s ease;
        }
        
        /* На ПК добавляем отступ для основного контента */
        @media (min-width: 768px) {
            body.has-sidebar .main-content {
                margin-left: 240px;
                width: calc(100% - 240px);
            }
        }
        
        /* На мобильных растягиваем контент на всю ширину */
        @media (max-width: 767px) {
            .main-content {
                margin-left: 0 !important;
                width: 100% !important;
            }
        }
    `;
    document.head.appendChild(globalStyles);

    // HTML структура сайдбара
    const sidebarHTML = `
        <div class="sidebar">
            <style>
                .sidebar {
                    width: 240px;
                    height: 100vh;
                    background: #121212;
                    color: #e0e0e0;
                    position: fixed;
                    left: 0;
                    top: 0;
                    z-index: 1000;
                    box-shadow: 3px 0 15px rgba(0,0,0,0.6);
                    overflow-y: auto;
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.1);
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    -ms-overflow-style: none;
                    scrollbar-width: none;
                }
                
                .sidebar::-webkit-scrollbar {
                    display: none;
                }
                
                /* Скрываем сайдбар на мобильных устройствах */
                @media (max-width: 767px) {
                    .sidebar {
                        display: none !important;
                    }
                }
                
                .sidebar:hover {
                    box-shadow: 3px 0 20px rgba(0,0,0,0.8);
                }
                
                .nav {
                    padding: 20px 0;
                    height: 100%;
                    overflow-y: auto;
                    -ms-overflow-style: none;
                    scrollbar-width: none;
                }
                
                .nav::-webkit-scrollbar {
                    display: none;
                }
                
                .nav-item {
                    position: relative;
                    overflow: hidden;
                }
                
                .nav-link {
                    color: #e0e0e0 !important;
                    padding: 14px 25px;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    transition: all 0.3s ease;
                    position: relative;
                    z-index: 2;
                    font-size: 16px;
                    text-decoration: none;
                }
                
                .nav-link:hover {
                    background: rgba(64, 126, 201, 0.2);
                    padding-left: 28px;
                }
                
                .nav-link.active {
                    background: linear-gradient(90deg, rgba(64, 126, 201, 0.8), transparent);
                    border-left: 4px solid #407ec9;
                    font-weight: 600;
                }
                
                .nav-link i {
                    width: 24px;
                    text-align: center;
                    transition: transform 0.3s ease;
                    color: #a0c4ff;
                }
                
                .submenu {
                    background: rgba(30, 30, 30, 0.9);
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
                    padding: 12px 25px 12px 60px;
                    font-size: 15px;
                    opacity: 0.9;
                    color: #d0d0d0 !important;
                }
                
                .submenu .nav-link:hover {
                    background: rgba(64, 126, 201, 0.15);
                    padding-left: 63px;
                    color: #ffffff !important;
                }
                
                .rotate-icon {
                    transform: rotate(180deg);
                }
                
                .nav-link .fa-chevron-down {
                    margin-left: auto;
                    transition: transform 0.4s cubic-bezier(0.68, -0.55, 0.27, 1.55);
                    color: #a0c4ff;
                    font-size: 14px;
                }
                
                .nav-item::after {
                    content: '';
                    position: absolute;
                    bottom: 0;
                    left: 20px;
                    right: 20px;
                    height: 1px;
                    background: rgba(80, 80, 80, 0.5);
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
                
                /* Обновленный блок пользователя */
                .user-area {
                    padding: 25px 20px 15px;
                    text-align: center;
                    border-bottom: 1px solid rgba(80, 80, 80, 0.5);
                    margin-bottom: 15px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 10px;
                }
                
                .sidebar-avatar {
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #1a2138, #0e1321);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 1.5rem;
                    cursor: pointer;
                    border: 2px solid #407ec9;
                    box-shadow: 0 0 10px rgba(64, 126, 201, 0.5);
                    overflow: hidden;
                }
                
                .sidebar-avatar-placeholder {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 100%;
                    height: 100%;
                    border-radius: 50%;
                    font-weight: bold;
                    font-size: 1.2rem;
                    text-shadow: 0 0 8px rgba(64, 126, 201, 0.8);
                }
                
                .user-details {
                    text-align: center;
                    cursor: pointer;
                }
                
                .user-name {
                    font-weight: 600;
                    color: #e0e0e0;
                    font-size: 16px;
                    margin-bottom: 3px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    max-width: 200px;
                }
                
                .user-balance {
                    font-weight: 500;
                    color: #a0c4ff;
                    font-size: 14px;
                }
                
                .user-login-text {
                    font-weight: 600;
                    color: #e0e0e0;
                    font-size: 16px;
                    text-shadow: 0 0 5px #00c6ff, 0 0 10px #00c6ff;
                    margin-top: 8px;
                }
                
                .admin-badge {
                    font-weight: 500;
                    color: #ffcc00;
                    font-size: 14px;
                    margin-top: 3px;
                }
            </style>
            
            <!-- Обновленный блок пользователя -->
            <div class="user-area" id="sidebarUserArea">
                <div class="sidebar-avatar" id="sidebarAvatar"></div>
                <div class="user-details" id="userDetails"></div>
            </div>
            
            <ul class="nav flex-column">
                <!-- Меню (без изменений) -->
                <li class="nav-item">
                    <a class="nav-link active" href="/">
                        <i class="fas fa-home"></i>
                        <span>მთავარი</span>
                    </a>
                </li>
                
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

    // Функция инициализации сайдбара
    function initSidebar() {
        const sidebarContainer = document.getElementById('sidebar-container');
        if (!sidebarContainer) return;
        
        sidebarContainer.innerHTML = '';
        
        if (window.innerWidth >= 768) {
            sidebarContainer.innerHTML = sidebarHTML;
            document.body.classList.add('has-sidebar');
            setupSidebar();
            updateUserInfo(); // Инициализация информации о пользователе
        } else {
            document.body.classList.remove('has-sidebar');
        }
    }

    // Функция обновления информации о пользователе
    function updateUserInfo() {
        const userData = window.currentUser || {};
        const avatarEl = document.getElementById('sidebarAvatar');
        const detailsEl = document.getElementById('userDetails');
        
        if (!avatarEl || !detailsEl) return;
        
        // Очищаем предыдущее содержимое
        avatarEl.innerHTML = '';
        detailsEl.innerHTML = '';
        
        if (userData.first_name && userData.last_name) {
            // Пользователь авторизован
            const initials = `${userData.first_name.charAt(0)}${userData.last_name.charAt(0)}`;
            const avatarColor = userData.avatar_color || '#1a2138';
            const balance = userData.balance ? userData.balance.toFixed(2) : '0.00';
            
            // Создаем аватар
            avatarEl.innerHTML = `
                <div class="sidebar-avatar-placeholder" style="background: ${avatarColor}">
                    ${initials}
                </div>
            `;
            
            // Создаем информацию о пользователе
            detailsEl.innerHTML = `
                <div class="user-name">${userData.first_name} ${userData.last_name}</div>
                <div class="user-balance">ბალანსი: ${balance}₾</div>
                ${userData.is_admin ? '<div class="admin-badge">ადმინისტრატორი</div>' : ''}
            `;
            
            // Добавляем обработчики
            avatarEl.onclick = () => window.location.href = "/user/dashboard";
            detailsEl.onclick = () => window.location.href = "/user/dashboard";
        } else {
            // Пользователь не авторизован
            avatarEl.innerHTML = `
                <div class="sidebar-avatar-placeholder">KODI.GE</div>
            `;
            
            detailsEl.innerHTML = `
                <div class="user-login-text">ლოგინი | რეგისტრაცია</div>
            `;
            
            // Добавляем обработчики
            avatarEl.onclick = () => window.location.href = "/login";
            detailsEl.onclick = () => window.location.href = "/login";
        }
    }

    // Функция настройки поведения сайдбара
    function setupSidebar() {
        // Переключение подменю
        const toggleSubmenu = (buttonClass, menuId) => {
            const button = document.querySelector(buttonClass);
            const menu = document.getElementById(menuId);
            const icon = button?.querySelector('.fa-chevron-down');
            
            if (button && menu && icon) {
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    
                    // Закрываем другие подменю
                    document.querySelectorAll('.submenu').forEach(sub => {
                        if (sub !== menu && sub.classList.contains('show')) {
                            sub.classList.remove('show');
                            const otherIcon = sub.closest('.nav-item')?.querySelector('.fa-chevron-down');
                            if (otherIcon) {
                                otherIcon.classList.remove('rotate-icon');
                                otherIcon.style.transform = 'rotate(0deg)';
                            }
                        }
                    });
                    
                    // Переключаем текущее подменю
                    menu.classList.toggle('show');
                    icon.classList.toggle('rotate-icon');
                    icon.style.transform = icon.classList.contains('rotate-icon') ? 'rotate(180deg)' : 'rotate(0deg)';
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
        
        // Подсветка активного пункта меню
        const currentPath = window.location.pathname;
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }

    // Инициализация при загрузке
    initSidebar();
    
    // Обновление при изменении размера окна
    window.addEventListener('resize', function() {
        initSidebar();
        
        if (window.innerWidth >= 768) {
            document.body.classList.add('has-sidebar');
        } else {
            document.body.classList.remove('has-sidebar');
        }
    });
    
    // Добавляем Font Awesome, если он еще не подключен
    if (!document.querySelector('link[href*="font-awesome"]')) {
        const fontAwesome = document.createElement('link');
        fontAwesome.rel = 'stylesheet';
        fontAwesome.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
        document.head.appendChild(fontAwesome);
    }
    
    // Обновляем информацию при изменении статуса авторизации
    window.addEventListener('userAuthChange', updateUserInfo);
});
