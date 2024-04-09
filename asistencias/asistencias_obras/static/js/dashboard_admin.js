document.getElementById('logoutLink').addEventListener('click', function() {
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = this.getAttribute('data-url'); // Obtener la URL desde el atributo de datos

    // CSRF token
    var csrfToken = document.createElement('input');
    csrfToken.type = 'hidden';
    csrfToken.name = 'csrfmiddlewaretoken';
    csrfToken.value = '{{ csrf_token }}'; // Esto necesitará ser ajustado si estás en un archivo .js
    form.appendChild(csrfToken);

    document.body.appendChild(form);
    form.submit();
});
window.addEventListener('load', function() {
console.log('La página ha terminado de cargar');
document.getElementById('loading').style.display = 'none';
});

document.addEventListener('alpine:init', () => {
    Alpine.data('navbar', () => ({
        isOpen: false,
        openDropdown: false,
        toggleMenu() {
            this.isOpen = !this.isOpen;
        },
        toggleDropdown() {
            this.openDropdown = !this.openDropdown;
        }
    }));
});

