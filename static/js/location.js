document.addEventListener('DOMContentLoaded', function () {
    const countryInput = document.getElementById('country-input');
    const stateInput = document.getElementById('state-input');
    const districtInput = document.getElementById('district-input');
    const statesDatalist = document.getElementById('states');
    const districtsDatalist = document.getElementById('districts');

    // Minimal mapping for progressive enhancement. If country isn't in this map,
    // the datalist remains empty but typing is always allowed.
    const countryToStates = {
        'United States of America': [
            'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware',
            'Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana',
            'Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana',
            'Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina',
            'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina',
            'South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming'
        ],
        'India': [
            'Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana','Himachal Pradesh',
            'Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland',
            'Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal',
            'Delhi'
        ],
        'United Kingdom': [
            'England','Scotland','Wales','Northern Ireland'
        ],
        'Canada': [
            'Alberta','British Columbia','Manitoba','New Brunswick','Newfoundland and Labrador','Nova Scotia','Ontario','Prince Edward Island','Quebec','Saskatchewan'
        ],
        'Australia': [
            'New South Wales','Queensland','South Australia','Tasmania','Victoria','Western Australia','Australian Capital Territory','Northern Territory'
        ]
    };

    // Optional district samples for a few states (example for India)
    const stateToDistricts = {
        'Karnataka': ['Bengaluru Urban','Mysuru','Mangalore','Dharwad'],
        'Maharashtra': ['Mumbai','Pune','Nagpur','Nashik'],
        'California': ['Los Angeles','San Diego','San Francisco','Sacramento']
    };

    function populateDatalist(datalistEl, items) {
        // Remove existing options
        while (datalistEl.firstChild) datalistEl.removeChild(datalistEl.firstChild);
        if (!items || items.length === 0) return;
        const frag = document.createDocumentFragment();
        items.forEach(function (it) {
            const opt = document.createElement('option');
            opt.value = it;
            frag.appendChild(opt);
        });
        datalistEl.appendChild(frag);
    }

    if (!countryInput) return; // nothing to do

    countryInput.addEventListener('change', function () {
        const country = countryInput.value;
        const states = countryToStates[country] || [];
        populateDatalist(statesDatalist, states);

        // clear state/district values when country changes to avoid stale selection
        if (stateInput) stateInput.value = '';
        if (districtInput) districtInput.value = '';
        populateDatalist(districtsDatalist, []);
    });

    if (stateInput) {
        stateInput.addEventListener('change', function () {
            const state = stateInput.value;
            const dists = stateToDistricts[state] || [];
            populateDatalist(districtsDatalist, dists);
            if (districtInput) districtInput.value = '';
        });
    }

});
