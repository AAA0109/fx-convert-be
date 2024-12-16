jQuery(document).ready(function ($) {
    (function ($) {
        $(function () {
            var selectField = $('.field-data_type select');

            function toggleSelect(select) {
                var value = select.val(),
                sftp_elements = [
                    select.closest('#dataprovider_form').find('.column-sftp_host'),
                    select.closest('#dataprovider_form').find('.column-sftp_port'),
                    select.closest('#dataprovider_form').find('.column-sftp_username'),
                    select.closest('#dataprovider_form').find('.column-sftp_password'),
                    select.closest('#dataprovider_form').find('.column-sftp_dir'),
                    select.closest('#dataprovider_form').find('.field-sftp_host'),
                    select.closest('#dataprovider_form').find('.field-sftp_port'),
                    select.closest('#dataprovider_form').find('.field-sftp_username'),
                    select.closest('#dataprovider_form').find('.field-sftp_password'),
                    select.closest('#dataprovider_form').find('.field-sftp_dir')
                ];

                if (value !== 'sftp') {
                    sftp_elements.forEach(el => el.hide())
                } else {
                     sftp_elements.forEach(el => el.show())
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

