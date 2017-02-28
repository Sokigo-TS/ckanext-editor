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