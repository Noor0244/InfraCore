// Minimal helper to enable dependent datalist UX for country/state/district without changing backend
// This file provides lightweight filtering of datalists for better UX.
(function(){
    function attachFilter(inputId, dataListId){
        var input = document.getElementById(inputId);
        var list = document.getElementById(dataListId);
        if(!input || !list) return;
        var options = Array.from(list.options).map(function(o){ return o.value; });
        input.addEventListener('input', function(){
            var val = this.value.toLowerCase();
            // simple filter: if typed value doesn't match any option, keep the list but don't change options
            // we don't modify the DOM options to avoid breaking server-side expectations
            // Instead, if a clear match exists, set datalist value suggestion by selecting first match
            var match = options.find(function(o){ return o.toLowerCase().indexOf(val) === 0; });
            // allow typing freely; no forced selection
            // But we can set a placeholder suggestion via title
            if(match){ this.title = 'Suggestion: '+match; } else { this.title = ''; }
        });
    }

    attachFilter('country-input','country_list');
    attachFilter('state-input','state_list');
    attachFilter('district-input','district_list');
})();
