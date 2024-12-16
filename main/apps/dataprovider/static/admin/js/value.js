jQuery(document).ready(function ($) {
    (function ($) {
        $(function () {
            var selectField = $('#id_mapping_type'),
                to_value_field = $('.field-to_value'),
                to_currency_field = $('.field-to_currency'),
                to_fxpair_field = $('.field-to_fxpair');

            function toggleSelect(value) {
                if (value === 'text') {
                    to_value_field.show();
                    to_currency_field.hide();
                    to_fxpair_field.hide();
                } else if (value === 'currency') {
                    to_value_field.hide();
                    to_currency_field.show();
                    to_fxpair_field.hide();
                } else if (value === 'fxpair') {
                    to_value_field.hide();
                    to_currency_field.hide();
                    to_fxpair_field.show();
                }
            }

            // show/hide on load based on pervious value of selectField
            toggleSelect(selectField.val());

            // show/hide on change
            selectField.change(function () {
                toggleSelect($(this).val());
            });
        });
    })(django.jQuery);
});

