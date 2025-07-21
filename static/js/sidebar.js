document.addEventListener('DOMContentLoaded', function() {
    const sidebarHTML = `
        <div class="sidebar">
            <ul class="nav flex-column">
                <li class="nav-item">
                    <a class="nav-link active" href="#">
                        <i class="fas fa-home"></i>
                        <span>მთავარი</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" data-bs-toggle="collapse" data-bs-target="#appleSubmenu">
                        <i class="fas fa-mobile-alt"></i>
                        <span>შემოწმება Apple</span>
                        <i class="fas fa-chevron-down float-end"></i>
                    </a>
                    <div class="collapse" id="appleSubmenu">
                        <div class="submenu">
                            <a class="nav-link" href="/applecheck?type=free">
                                <i class="fas fa-check-circle"></i>
                                <span>უფასო შემოწმება</span>
                            </a>
                            <a class="nav-link" href="/applecheck?type=fmi">
                                <i class="fas fa-shopping-cart"></i>
                                <span>პლატანი შემოწმება</span>
                            </a>
                            <a class="nav-link" href="/applecheck?type=premium">
                                <i class="fas fa-crown"></i>
                                <span>პრემიუმ შემოწმება</span>
                            </a>
                        </div>
                    </div>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/androidcheck">
                        <i class="fab fa-android"></i>
                        <span>შემოწმება Android</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link disabled" href="#">
                        <i class="fas fa-unlock-alt"></i>
                        <span>ტელეფონის განბლოკვა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/compare">
                        <i class="fas fa-exchange-alt"></i>
                        <span>ტელეფონების შედარება</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/knowledge-base">
                        <i class="fas fa-book"></i>
                        <span>ცოდნის ბაზა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/contacts">
                        <i class="fas fa-address-card"></i>
                        <span>კონტაქტი</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-shield-alt"></i>
                        <span>კონფიდენციალურობის პოლიტიკა</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#">
                        <i class="fas fa-undo"></i>
                        <span>დაბრუნების პოლიტიკა</span>
                    </a>
                </li>
            </ul>
        </div>
    `;

    // Вставляем сайдбар в контейнер
    const sidebarContainer = document.getElementById('sidebar-container');
    if (sidebarContainer) {
        sidebarContainer.innerHTML = sidebarHTML;
    }

    // Инициализация Bootstrap компонентов
    const collapseTriggers = document.querySelectorAll('[data-bs-toggle="collapse"]');
    collapseTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const target = document.querySelector(this.dataset.bsTarget);
            if (target) {
                new bootstrap.Collapse(target, {
                    toggle: true
                });
            }
        });
    });
});
