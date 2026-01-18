// Global DD/MM/YYYY date input formatter for all text inputs with placeholder DD/MM/YYYY
(function() {
    function formatDateInput(input) {
        if (!input || input._dateFormatHandler) return;
        input.addEventListener('input', function(e) {
            let value = input.value.replace(/\D/g, '').slice(0, 8); // Only digits, max 8 (DDMMYYYY)
            let formatted = '';
            if (value.length > 0) {
                formatted += value.substring(0, 2);
            }
            if (value.length > 2) {
                formatted += '/' + value.substring(2, 4);
            }
            if (value.length > 4) {
                formatted += '/' + value.substring(4, 8);
            }
            input.value = formatted;
        });
        input.setAttribute('maxlength', '10');
        input.setAttribute('pattern', '\\d{2}/\\d{2}/\\d{4}');
        input.setAttribute('inputmode', 'numeric');
        input.placeholder = 'DD/MM/YYYY';
        input._dateFormatHandler = true;
    }
    function applyToAllDateInputs(singleInput) {
        if (singleInput) {
            formatDateInput(singleInput);
        } else {
            var inputs = document.querySelectorAll('input[type="text"][placeholder="DD/MM/YYYY"], input[type="text"][placeholder*="DD/MM/YYYY"]');
            for (var i = 0; i < inputs.length; i++) {
                formatDateInput(inputs[i]);
            }
        }
    }
    // Expose globally for dynamic forms
    window.applyToAllDateInputs = applyToAllDateInputs;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyToAllDateInputs);
    } else {
        applyToAllDateInputs();
    }
})();
