function getParameterByName(name, url, as_list) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, '\\$&');

    if (as_list){
        var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)', 'g');

        params = [];

        while (tokens = regex.exec(url)) {
            params.push(decodeURIComponent(tokens[2].replace(/\+/g, ' ')));
        }

        return params;
    }

    var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
    results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function addFieldToParameters(field){
    var q = getParameterByName('q');
    var sort = getParameterByName('sort');

    var res_format = getParameterByName('res_format', null, true);
    var vocab_geographical_coverage = getParameterByName('vocab_geographical_coverage', null, true);
    var groups = getParameterByName('groups', null, true);
    var organization = getParameterByName('organization', null, true);
    var collections = getParameterByName('collections', null, true);

    var query = 'editor?';

    if (q){
        query += 'q=' + q;
    }

    if (sort){
        query += '&sort=' + sort;
    }

    if ( res_format.length) {
        query += '&res_format=' + res_format.join('&res_format=')
    }

    if ( vocab_geographical_coverage.length) {
        query += '&vocab_geographical_coverage=' + vocab_geographical_coverage.join('&vocab_geographical_coverage=')
    }

    if ( groups.length) {
        query += '&groups=' + groups.join('&groups=')
    }

    if ( organization.length) {
        query += '&organization=' + organization.join('&organization=')
    }

    if ( collections.length) {
        query += '&collections=' + collections.join('&collections=')
    }

    query += '&_field=' + field;

    window.location = query;

}

$(document).ready(function() {
    $('#select-all').click(function(event) {
        if(this.checked) {
            $(':checkbox').each(function() {
                this.checked = true;
            });
        }
        else {
            $(':checkbox').each(function() {
                this.checked = false;
            });
        }
    });

    $("#editor-form-submit").click(function(event){
        if(!confirm ("Are you sure you want to edit the selected datasets?")) {
            event.preventDefault();
        }
    });
});