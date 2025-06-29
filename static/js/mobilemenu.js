// static/js/mobilemenu.js

// Создаем HTML структуру мобильного меню
function createMobileMenuStructure() {
    const mobileMenuContainer = document.getElementById('mobile-menu-container');
    if (!mobileMenuContainer) return;
    
    mobileMenuContainer.innerHTML = `
        <!-- Mobile Menu Modal -->
        <div class="mobile-menu-modal" id="mobileMenuModal">
            <div class="modal-content">
                <button class="close-modal" onclick="closeMobileMenu()">
                    <i class="fas fa-times"></i>
                </button>
                
                <div class="floating-avatar-container">
                    <div class="floating-avatar" onclick="goToLogin()">
                        <div class="avatar-placeholder">KODI.GE</div>
                    </div>
                    <div class="user-info-container">
                        <div onclick="goToLogin()">
                            ლოგინი|რეგისტრაცია
                        </div>
                    </div>
                </div>
                
                <div class="modal-body">
                    <div class="menu-grid">
                        <a class="menu-item" href="/" onclick="closeAllMobileMenus();">
                            <i class="fas fa-home"></i>
                            <span>მთავარი</span>
                        </a>
                        <div class="menu-item" onclick="openAppleSubmenu()">
                            <i class="fab fa-apple"></i>
                            <span>Apple</span>
                        </div>
                        <div class="menu-item" onclick="openAndroidSubmenu()">
                            <i class="fab fa-android"></i>
                            <span>Android</span>
                        </div>
                        <div class="menu-item disabled">
                            <i class="fas fa-unlock-alt"></i>
                            <span>განბლოკვა</span>
                        </div>
                        <a class="menu-item" href="/compare" onclick="closeAllMobileMenus();">
                            <i class="fas fa-exchange-alt"></i>
                            <span>შედარება</span>
                        </a>
                        <a class="menu-item" href="/knowledge-base" onclick="closeAllMobileMenus();">
                            <i class="fas fa-book"></i>
                            <span>ცოდნის ბაზა</span>
                        </a>
                        <a class="menu-item" href="/contacts" onclick="closeAllMobileMenus();">
                            <i class="fas fa-address-card"></i>
                            <span>კონტაქტი</span>
                        </a>
                        <div class="menu-item">
                            <i class="fas fa-shield-alt"></i>
                            <span>კონფიდენციალურობა</span>
                        </div>
                        <div class="menu-item">
                            <i class="fas fa-undo"></i>
                            <span>დაბრუნება</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Apple Submenu Modal -->
        <div class="mobile-menu-modal" id="appleSubmenuModal">
            <div class="modal-content">
                <button class="close-modal" onclick="closeAppleSubmenu()">
                    <i class="fas fa-times"></i>
                </button>

                <div class="floating-avatar-container">
                    <div class="floating-avatar" onclick="goToLogin()">
                        <div class="avatar-placeholder">KODI.GE</div>
                    </div>
                    <div class="user-info-container">
                        <div onclick="goToLogin()">
                            ლოგინი/რეგისტრაცია
                        </div>
                    </div>
                </div>
                
                <div class="modal-body">
                    <div class="menu-grid">
                        <a class="menu-item" href="/applecheck?type=free" onclick="closeAllMobileMenus();">
                            <img src="static/ico/8f1197c9-19f4-4923-8030-4f7b88c9d697_20250627_012614_0000.png" 
                                 class="menu-icon-img">
                            <span>უფასო შემოწმება</span>
                        </a>
                        <a class="menu-item" href="/applecheck?type=fmi" onclick="closeAllMobileMenus();">
                            <img src="static/ico/f9a07c0e-e427-4a1a-aab9-948ba60f1b6a_20250627_012716_0000.png" 
                                 class="menu-icon-img">
                            <span>FMI iCloud</span>
                        </a>
                        <a class="menu-item" href="/applecheck?type=sim_lock" onclick="closeAllMobileMenus();">
                            <img src="static/ico/957afe67-7a27-48cb-9622-6c557b220b71_20250627_012808_0000.png" 
                                 class="menu-icon-img">
                            <span>SIM ლოკი</span>
                        </a>
                        <a class="menu-item" href="/applecheck?type=blacklist" onclick="closeAllMobileMenus();">
                            <img src="static/ico/4e28c4f2-541b-4a1b-8163-c79e6db5481c_20250627_012852_0000.png" 
                                 class="menu-icon-img">
                            <span>შავი სია</span>
                        </a>
                        <a class="menu-item" href="/applecheck?type=mdm" onclick="closeAllMobileMenus();">
                            <img src="static/ico/275e6a62-c55e-48b9-8781-5b323ebcdce0_20250627_012946_0000.png" 
                                 class="menu-icon-img">
                            <span>MDM ბლოკი</span>
                        </a>
                        <a class="menu-item" href="/applecheck?type=premium" onclick="closeAllMobileMenus();">
                            <img src="static/ico/84df4824-0564-447c-b5c4-e749442bdc19_20250627_013110_0000.png" 
                                 class="menu-icon-img">
                            <span>პრემიუმ შემოწმება</span>
                        </a>
                        <a class="menu-item" href="#" onclick="alert('სერვისი მომზადების პროცესშია'); closeAllMobileMenus();">
                            <img src="static/ico/874fae5b-c0f5-42d8-9c37-679aa86360e6_20250627_013030_0000.png" 
                                 class="menu-icon-img">
                            <span>MacBook</span>
                        </a>
                        <div class="menu-item" onclick="closeAppleSubmenu()">
                            <i class="fas fa-arrow-left"></i>
                            <span>უკან</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Android Submenu Modal -->
        <div class="mobile-menu-modal" id="androidSubmenuModal">
            <div class="modal-content">
                <button class="close-modal" onclick="closeAndroidSubmenu()">
                    <i class="fas fa-times"></i>
                </button>

                <div class="floating-avatar-container">
                    <div class="floating-avatar" onclick="goToLogin()">
                        <div class="avatar-placeholder">KODI.GE</div>
                    </div>
                    <div class="user-info-container">
                        <div onclick="goToLogin()">
                            ლოგინი/რეგისტრაცია
                        </div>
                    </div>
                </div>
                
                <div class="modal-body">
                    <div class="menu-grid">
                        <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                            <i class="fab fa-samsung"></i>
                            <span>Samsung</span>
                        </a>
                        <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                            <i class="fas fa-bolt"></i>
                            <span>Xiaomi</span>
                        </a>
                        <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                            <i class="fab fa-google"></i>
                            <span>Pixel</span>
                        </a>
                        <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                            <i class="fab fa-huawei"></i>
                            <span>Huawei</span>
                        </a>
                        <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                            <i class="fas fa-circle"></i>
                            <span>Oppo</span>
                        </a>
                        <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                            <i class="fab fa-android"></i>
                            <span>LG</span>
                        </a>
                        <a class="menu-item" href="/androidcheck" onclick="closeAllMobileMenus();">
                            <i class="fas fa-ellipsis-h"></i>
                            <span>სხვა</span>
                        </a>
                        <div class="menu-item" onclick="closeAndroidSubmenu()">
                            <i class="fas fa-arrow-left"></i>
                            <span>უკან</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Функции для блокировки прокрутки фона
function lockBodyScroll() {
  const scrollY = window.scrollY;
  document.body.style.top = `-${scrollY}px`;
  document.body.classList.add('fixed-body');
}

function unlockBodyScroll() {
  const scrollY = -parseInt(document.body.style.top || '0', 10);
  document.body.classList.remove('fixed-body');
  document.body.style.top = '';
  window.scrollTo(0, scrollY);
}

// Mobile menu functions
function openMobileMenu() {
    try {
        const modal = document.getElementById('mobileMenuModal');
        if (modal) {
            modal.style.display = 'block';
            setTimeout(() => {
                modal.classList.add('open');
            }, 10);
            lockBodyScroll();
        }
    } catch(e) {
        console.error('Error opening mobile menu:', e);
    }
}

function closeMobileMenu() {
    try {
        const modal = document.getElementById('mobileMenuModal');
        if (modal) {
            modal.classList.remove('open');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
            unlockBodyScroll();
        }
    } catch(e) {
        console.error('Error closing mobile menu:', e);
    }
}

function openAppleSubmenu() {
    try {
        closeMobileMenu();
        const appleModal = document.getElementById('appleSubmenuModal');
        if (appleModal) {
            appleModal.style.display = 'block';
            setTimeout(() => {
                appleModal.classList.add('open');
            }, 10);
            lockBodyScroll();
        }
    } catch(e) {
        console.error('Error opening Apple submenu:', e);
    }
}

function closeAppleSubmenu() {
    try {
        const appleModal = document.getElementById('appleSubmenuModal');
        if (appleModal) {
            appleModal.classList.remove('open');
            setTimeout(() => {
                appleModal.style.display = 'none';
                openMobileMenu();
            }, 300);
            unlockBodyScroll();
        }
    } catch(e) {
        console.error('Error closing Apple submenu:', e);
    }
}

function openAndroidSubmenu() {
    try {
        closeMobileMenu();
        const androidModal = document.getElementById('androidSubmenuModal');
        if (androidModal) {
            androidModal.style.display = 'block';
            setTimeout(() => {
                androidModal.classList.add('open');
            }, 10);
            lockBodyScroll();
        }
    } catch(e) {
        console.error('Error opening Android submenu:', e);
    }
}

function closeAndroidSubmenu() {
    try {
        const androidModal = document.getElementById('androidSubmenuModal');
        if (androidModal) {
            androidModal.classList.remove('open');
            setTimeout(() => {
                androidModal.style.display = 'none';
                openMobileMenu();
            }, 300);
            unlockBodyScroll();
        }
    } catch(e) {
        console.error('Error closing Android submenu:', e);
    }
}

function closeAllMobileMenus() {
    closeMobileMenu();
    closeAppleSubmenu();
    closeAndroidSubmenu();
    unlockBodyScroll();
}

// Redirect to login
function goToLogin() {
    closeAllMobileMenus();
    window.location.href = "/login";
}

// Initialize mobile menu when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Создаем HTML структуру меню
    createMobileMenuStructure();
    
    // Добавляем CSS для фиксации фона и анимации снизу
    const style = document.createElement('style');
    style.textContent = `
        .fixed-body {
            position: fixed;
            width: 100%;
            overflow: hidden;
        }
        
        .mobile-menu-modal {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: auto;
            max-height: 85vh;
            background: white;
            display: none;
            z-index: 1000;
            border-radius: 20px 20px 0 0;
            box-shadow: 0 -5px 20px rgba(0,0,0,0.2);
            transform: translateY(100%);
            transition: transform 0.3s ease-out;
        }
        
        .mobile-menu-modal.open {
            transform: translateY(0);
        }
        
        .modal-content {
            padding: 20px;
            position: relative;
            max-height: 85vh;
            overflow-y: auto;
        }
        
        .close-modal {
            position: absolute;
            top: 15px;
            right: 15px;
            background: none;
            border: none;
            font-size: 1.2rem;
            cursor: pointer;
            z-index: 1010;
            color: #666;
        }
        
        .floating-avatar-container {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        
        .floating-avatar {
            width: 50px;
            height: 50px;
            background: #f5f5f5;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
        }
        
        .user-info-container {
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
        }
        
        .menu-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }
        
        .menu-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 10px;
            border-radius: 10px;
            background: #f9f9f9;
            cursor: pointer;
            transition: all 0.2s ease;
            min-height: 90px;
            justify-content: center;
        }
        
        .menu-item:hover {
            background: #f0f0f0;
        }
        
        .menu-item i {
            font-size: 24px;
            margin-bottom: 8px;
            color: #555;
        }
        
        .menu-item span {
            font-size: 12px;
            line-height: 1.3;
        }
        
        .menu-icon-img {
            width: 24px;
            height: 24px;
            margin-bottom: 8px;
            object-fit: contain;
        }
        
        .disabled {
            opacity: 0.5;
            pointer-events: none;
        }
        
        /* Оверлей для фона */
        .mobile-menu-modal::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: -1;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .mobile-menu-modal.open::before {
            opacity: 1;
        }
    `;
    document.head.appendChild(style);

    // Mobile menu button setup
    try {
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', openMobileMenu);
        } else {
            console.warn('Mobile menu button not found');
        }
    } catch(e) {
        console.error('Mobile menu setup error:', e);
    }

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        try {
            const mobileMenuModal = document.getElementById('mobileMenuModal');
            const appleSubmenuModal = document.getElementById('appleSubmenuModal');
            const androidSubmenuModal = document.getElementById('androidSubmenuModal');
            
            // Close mobile menu if click is outside
            if (mobileMenuModal && mobileMenuModal.classList.contains('open') && 
                !mobileMenuModal.contains(e.target) && 
                e.target.id !== 'mobileMenuBtn') {
                closeMobileMenu();
            }
            
            // Close apple submenu if click is outside
            if (appleSubmenuModal && appleSubmenuModal.classList.contains('open') && 
                !appleSubmenuModal.contains(e.target) && 
                e.target.id !== 'mobileMenuBtn') {
                closeAppleSubmenu();
            }
            
            // Close android submenu if click is outside
            if (androidSubmenuModal && androidSubmenuModal.classList.contains('open') && 
                !androidSubmenuModal.contains(e.target) && 
                e.target.id !== 'mobileMenuBtn') {
                closeAndroidSubmenu();
            }
        } catch(e) {
            console.error('Click handler error:', e);
        }
    });
    
    // Close menu when pressing Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllMobileMenus();
        }
    });
});
