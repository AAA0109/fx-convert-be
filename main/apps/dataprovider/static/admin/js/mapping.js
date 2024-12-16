jQuery(document).ready(function ($) {
    (function ($) {
        $(function () {
            var selectField = $('.field-mapping_type select');

            function toggleSelect(select) {
                var value = select.val(),
                    to_value_field = select.closest('.form-row').find('.field-to_value input'),
                    to_currency_field = select.closest('.form-row').find('.field-to_currency .related-widget-wrapper'),
                    to_fxpair_field = select.closest('.form-row').find('.field-to_fxpair .related-widget-wrapper'),
                    to_ircurve_field = select.closest('.form-row').find('.field-to_ircurve .related-widget-wrapper');
                if (value === 'text') {
                    to_value_field.show();
                    to_currency_field.hide();
                    to_fxpair_field.hide();
                    to_ircurve_field.hide();
                } else if (value === 'currency') {
                    to_value_field.hide();
                    to_currency_field.show();
                    to_fxpair_field.hide();
                    to_ircurve_field.hide();
                } else if (value === 'fxpair') {
                    to_value_field.hide();
                    to_currency_field.hide();
                    to_fxpair_field.show();
                    to_ircurve_field.hide();
                } else if (value === 'ircurve') {
                    to_value_field.hide();
                    to_currency_field.hide();
                    to_fxpair_field.hide();
                    to_ircurve_field.show();
                }
            }

            // show/hide on load based on pervious value of selectField
            toggleSelect(selectField);

            // show/hide on change
            selectField.change(function () {
                toggleSelect($(this));
            });
        });
    })(django.jQuery);
});

