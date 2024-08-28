(function ($) {
    "use strict";
    
    // Dropdown on mouse hover
    $(document).ready(function () {
        function toggleNavbarMethod() {
            if ($(window).width() > 992) {
                $('.navbar .dropdown').on('mouseover', function () {
                    $('.dropdown-toggle', this).trigger('click');
                }).on('mouseout', function () {
                    $('.dropdown-toggle', this).trigger('click').blur();
                });
            } else {
                $('.navbar .dropdown').off('mouseover').off('mouseout');
            }
        }
        toggleNavbarMethod();
        $(window).resize(toggleNavbarMethod);
    });


    // Date and time picker
    $('.date').datetimepicker({
        format: 'L'
    });
    $('.time').datetimepicker({
        format: 'LT'
    });
    
    
    // Back to top button
    $(window).scroll(function () {
        if ($(this).scrollTop() > 100) {
            $('.back-to-top').fadeIn('slow');
        } else {
            $('.back-to-top').fadeOut('slow');
        }
    });
    $('.back-to-top').click(function () {
        $('html, body').animate({scrollTop: 0}, 1500, 'easeInOutExpo');
        return false;
    });


    // Price carousel
    $(".price-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1000,
        margin: 45,
        dots: false,
        loop: true,
        nav : true,
        navText : [
            '<i class="bi bi-arrow-left"></i>',
            '<i class="bi bi-arrow-right"></i>'
        ],
        responsive: {
            0:{
                items:1
            },
            992:{
                items:2
            },
            1200:{
                items:3
            }
        }
    });


    // Team carousel
    $(".team-carousel, .related-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1000,
        margin: 45,
        dots: false,
        loop: true,
        nav : true,
        navText : [
            '<i class="bi bi-arrow-left"></i>',
            '<i class="bi bi-arrow-right"></i>'
        ],
        responsive: {
            0:{
                items:1
            },
            992:{
                items:2
            }
        }
    });


    // Testimonials carousel
    $(".testimonial-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1000,
        items: 1,
        dots: true,
        loop: true,
    });
    
})(jQuery);

document.addEventListener('DOMContentLoaded', () => {
    const timeInput = document.getElementById('time-input');
    const timeDropdown = document.getElementById('time-dropdown');

    // Function to generate time slots
    const generateTimeSlots = () => {
        const times = [];
        for (let hour = 1; hour <= 12; hour++) {
            for (const period of ['AM', 'PM']) {
                times.push(`${hour}:00 ${period}`);
                times.push(`${hour}:30 ${period}`);
            }
        }
        return times;
    };

    // Populate the dropdown
    const populateDropdown = () => {
        const times = generateTimeSlots();
        times.forEach(time => {
            const div = document.createElement('div');
            div.textContent = time;
            div.addEventListener('click', () => {
                timeInput.value = time;
                timeDropdown.style.display = 'none';
            });
            timeDropdown.appendChild(div);
        });
    };

    populateDropdown();

    // Show/hide dropdown
    timeInput.addEventListener('click', () => {
        timeDropdown.style.display = timeDropdown.style.display === 'none' ? 'block' : 'none';
    });

    document.addEventListener('click', (event) => {
        if (!event.target.closest('.time-picker')) {
            timeDropdown.style.display = 'none';
        }
    });
});

  // When the window is fully loaded, remove the preloader
  