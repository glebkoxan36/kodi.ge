// Global variables for menu elements
let mobileMenu;
let appleSubmenu;
let androidSubmenu;

// Function to lock body scroll
function lockBodyScroll() {
  const scrollY = window.scrollY;
  document.body.style.top = `-${scrollY}px`;
  document.body.classList.add('fixed-body');
}

// Function to unlock body scroll
function unlockBodyScroll() {
  const scrollY = -parseInt(document.body.style.top || '0', 10);
  document.body.classList.remove('fixed-body');
  document.body.style.top = '';
  window.scrollTo(0, scrollY);
}

// Open mobile menu
function openMenu(event) {
  if (event) event.preventDefault();
  lockBodyScroll();
  if (mobileMenu) {
    mobileMenu.classList.add('open');
  }
}

// Close mobile menu
function closeMenu(event) {
  if (event) event.preventDefault();
  if (mobileMenu) {
    mobileMenu.classList.remove('open');
  }
  unlockBodyScroll();
}

// Toggle Apple submenu
function toggleAppleSubMenu(event) {
  if (event) event.preventDefault();
  if (appleSubmenu) {
    appleSubmenu.classList.toggle('open');
  }
}

// Toggle Android submenu
function toggleAndroidSubMenu(event) {
  if (event) event.preventDefault();
  if (androidSubmenu) {
    androidSubmenu.classList.toggle('open');
  }
}

// Close all mobile menus
function closeAllMobileMenus() {
  if (mobileMenu) mobileMenu.classList.remove('open');
  if (appleSubmenu) appleSubmenu.classList.remove('open');
  if (androidSubmenu) androidSubmenu.classList.remove('open');
  unlockBodyScroll();
}

// Redirect to login
function goToLogin() {
  closeAllMobileMenus();
  window.location.href = "/login";
}

// Create mobile menu structure
function createMobileMenuStructure() {
  const mobileMenuContainer = document.getElementById('mobile-menu-container');
  if (!mobileMenuContainer) return;
  
  mobileMenuContainer.innerHTML = `
    <div id="mobile-menu" class="mobile-menu">
      <button id="mobile-menu-close" class="close-btn">✕</button>
      
      <div class="user-section" onclick="goToLogin()">
        <div class="avatar">KODI.GE</div>
        <div class="user-info">ლოგინი|რეგისტრაცია</div>
      </div>
      
      <div class="menu-items">
        <a href="/" class="menu-item" onclick="closeAllMobileMenus()">
          <i class="fas fa-home"></i> მთავარი
        </a>
        
        <div class="menu-item submenu-toggle" id="mobile-apple-toggle">
          <i class="fab fa-apple"></i> Apple
        </div>
        
        <div id="mobile-apple-menu" class="submenu">
          <a href="/applecheck?type=free" onclick="closeAllMobileMenus()">
            <img src="static/ico/8f1197c9-19f4-4923-8030-4f7b88c9d697_20250627_012614_0000.png" 
                 class="menu-icon-img">
            <span>უფასო შემოწმება</span>
          </a>
          <a href="/applecheck?type=fmi" onclick="closeAllMobileMenus()">
            <img src="static/ico/f9a07c0e-e427-4a1a-aab9-948ba60f1b6a_20250627_012716_0000.png" 
                 class="menu-icon-img">
            <span>FMI iCloud</span>
          </a>
          <a href="/applecheck?type=sim_lock" onclick="closeAllMobileMenus()">
            <img src="static/ico/957afe67-7a27-48cb-9622-6c557b220b71_20250627_012808_0000.png" 
                 class="menu-icon-img">
            <span>SIM ლოკი</span>
          </a>
          <a href="/applecheck?type=blacklist" onclick="closeAllMobileMenus()">
            <img src="static/ico/4e28c4f2-541b-4a1b-8163-c79e6db5481c_20250627_012852_0000.png" 
                 class="menu-icon-img">
            <span>შავი სია</span>
          </a>
          <a href="/applecheck?type=mdm" onclick="closeAllMobileMenus()">
            <img src="static/ico/275e6a62-c55e-48b9-8781-5b323ebcdce0_20250627_012946_0000.png" 
                 class="menu-icon-img">
            <span>MDM ბლოკი</span>
          </a>
          <a href="/applecheck?type=premium" onclick="closeAllMobileMenus()">
            <img src="static/ico/84df4824-0564-447c-b5c4-e749442bdc19_20250627_013110_0000.png" 
                 class="menu-icon-img">
            <span>პრემიუმ შემოწმება</span>
          </a>
          <a href="#" onclick="alert('სერვისი მომზადების პროცესშია'); closeAllMobileMenus();">
            <img src="static/ico/874fae5b-c0f5-42d8-9c37-679aa86360e6_20250627_013030_0000.png" 
                 class="menu-icon-img">
            <span>MacBook</span>
          </a>
          <div class="menu-item back-btn" onclick="toggleAppleSubMenu(event)">
            <i class="fas fa-arrow-left"></i>
            <span>უკან</span>
          </div>
        </div>
        
        <div class="menu-item submenu-toggle" id="mobile-android-toggle">
          <i class="fab fa-android"></i> Android
        </div>
        
        <div id="mobile-android-menu" class="submenu">
          <a href="/androidcheck" onclick="closeAllMobileMenus()">
            <i class="fab fa-samsung"></i>
            <span>Samsung</span>
          </a>
          <a href="/androidcheck" onclick="closeAllMobileMenus()">
            <i class="fas fa-bolt"></i>
            <span>Xiaomi</span>
          </a>
          <a href="/androidcheck" onclick="closeAllMobileMenus()">
            <i class="fab fa-google"></i>
            <span>Pixel</span>
          </a>
          <a href="/androidcheck" onclick="closeAllMobileMenus()">
            <i class="fab fa-huawei"></i>
            <span>Huawei</span>
          </a>
          <a href="/androidcheck" onclick="closeAllMobileMenus()">
            <i class="fas fa-circle"></i>
            <span>Oppo</span>
          </a>
          <a href="/androidcheck" onclick="closeAllMobileMenus()">
            <i class="fab fa-android"></i>
            <span>LG</span>
          </a>
          <a href="/androidcheck" onclick="closeAllMobileMenus()">
            <i class="fas fa-ellipsis-h"></i>
            <span>სხვა</span>
          </a>
          <div class="menu-item back-btn" onclick="toggleAndroidSubMenu(event)">
            <i class="fas fa-arrow-left"></i>
            <span>უკან</span>
          </div>
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
  `;
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
  // Create menu structure
  createMobileMenuStructure();
  
  // Inject fixed-body CSS
  const style = document.createElement('style');
  style.type = 'text/css';
  style.textContent = `
    .fixed-body {
      position: fixed;
      width: 100%;
      left: 0;
      overflow-y: hidden;
    }
    .mobile-menu {
      position: fixed;
      top: 0;
      left: -100%;
      width: 80%;
      max-width: 320px;
      height: 100vh;
      background: white;
      z-index: 1000;
      transition: left 0.4s ease;
      overflow-y: auto;
      box-shadow: 2px 0 10px rgba(0,0,0,0.1);
    }
    .mobile-menu.open {
      left: 0;
    }
    .submenu {
      position: absolute;
      top: 0;
      left: 100%;
      width: 100%;
      height: 100%;
      background: white;
      z-index: 1010;
      transition: left 0.4s ease;
    }
    .submenu.open {
      left: 0;
    }
    .close-btn {
      position: absolute;
      top: 10px;
      right: 10px;
      background: none;
      border: none;
      font-size: 1.5rem;
      cursor: pointer;
      z-index: 1020;
    }
    .user-section {
      display: flex;
      align-items: center;
      padding: 20px;
      border-bottom: 1px solid #eee;
      cursor: pointer;
    }
    .avatar {
      width: 50px;
      height: 50px;
      background: #f0f0f0;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 15px;
      font-weight: bold;
      font-size: 12px;
      text-align: center;
      line-height: 1.2;
    }
    .menu-items {
      padding: 20px;
    }
    .menu-item, .submenu a {
      display: flex;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #f5f5f5;
      text-decoration: none;
      color: #333;
    }
    .menu-item i, .submenu i {
      margin-right: 15px;
      width: 24px;
      text-align: center;
      font-size: 18px;
    }
    .menu-icon-img {
      width: 24px;
      height: 24px;
      margin-right: 15px;
      object-fit: contain;
    }
    .submenu-toggle {
      cursor: pointer;
    }
    .back-btn {
      display: flex;
      align-items: center;
      padding: 15px 0;
      color: #007bff;
      cursor: pointer;
    }
    .disabled {
      opacity: 0.5;
      pointer-events: none;
    }
  `;
  document.head.appendChild(style);

  // Cache DOM elements
  mobileMenu = document.getElementById('mobile-menu');
  appleSubmenu = document.getElementById('mobile-apple-menu');
  androidSubmenu = document.getElementById('mobile-android-menu');
  
  const menuButton = document.getElementById('mobileMenuBtn');
  const closeMenuButton = document.getElementById('mobile-menu-close');
  const appleToggle = document.getElementById('mobile-apple-toggle');
  const androidToggle = document.getElementById('mobile-android-toggle');
  const loginElements = document.querySelectorAll('.user-section, .floating-avatar');

  // Event listeners
  if (menuButton) menuButton.addEventListener('click', openMenu);
  if (closeMenuButton) closeMenuButton.addEventListener('click', closeMenu);
  if (appleToggle) appleToggle.addEventListener('click', toggleAppleSubMenu);
  if (androidToggle) androidToggle.addEventListener('click', toggleAndroidSubMenu);
  
  // Login redirect handlers
  if (loginElements.length) {
    loginElements.forEach(element => {
      element.addEventListener('click', goToLogin);
    });
  }

  // Close menu when clicking outside
  document.addEventListener('click', (e) => {
    const isMenu = mobileMenu?.contains(e.target);
    const isButton = e.target === menuButton || menuButton?.contains(e.target);
    
    if (mobileMenu?.classList.contains('open') && !isMenu && !isButton) {
      closeAllMobileMenus();
    }
  });

  // Close menu when pressing Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllMobileMenus();
    }
  });
});
