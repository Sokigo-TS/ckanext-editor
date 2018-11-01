function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, '\\$&');
    var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)'),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function addFieldToParameters(field){
    var q = getParameterByName('q');
    var sort = getParameterByName('sort');

    var query = 'editor?';

    if (q){
        query += 'q=' + q;
    }

    if (sort){
        query += '&sort=' + sort;
    }

    query += '&_field=' + field;

    window.location = query;

}