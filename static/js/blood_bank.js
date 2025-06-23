document.addEventListener('DOMContentLoaded', function() {
    const donorForm = document.getElementById('donor-form');
    const searchButton = document.getElementById('search-button');
    const searchBloodGroup = document.getElementById('search-blood-group');
    const searchLocation = document.getElementById('search-location');
    const donorsContainer = document.getElementById('donors-container');
    const statsContainer = document.getElementById('stats-container');

    function renderDonors(donors) {
        donorsContainer.innerHTML = '';
        if (donors.length === 0) {
            donorsContainer.innerHTML = '<p>No donors found for the selected criteria.</p>';
            return;
        }
        donors.forEach(donor => {
            const card = document.createElement('div');
            card.className = 'donor-card';
            card.innerHTML = `
                <div class="donor-info">
                    <h4>${donor.name}</h4>
                    <p><strong>Blood Group:</strong> ${donor.blood_group}</p>
                    <p><strong>Location:</strong> ${donor.location}</p>
                    <p><strong>Contact:</strong> ${donor.contact}</p>
                    <p><strong>Registered:</strong> ${donor.created_at}</p>
                </div>
            `;
            donorsContainer.appendChild(card);
        });
    }

    function renderStatistics(statistics) {
        statsContainer.innerHTML = '';
        const bloodTypes = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

        bloodTypes.forEach(bloodType => {
            const percentage = statistics[bloodType] || 0;
            const card = document.createElement('div');
            card.className = 'stat-card';
            card.innerHTML = `
                <h3>${bloodType}</h3>
                <div class="stat-value">${percentage}%</div>
                <div class="stat-bar" style="--percentage: ${percentage}%"></div>
            `;
            statsContainer.appendChild(card);
        });
    }

    function loadStatistics() {
        fetch('/api/blood-statistics')
            .then(res => res.json())
            .then(data => {
                renderStatistics(data.statistics);
            })
            .catch(() => {
                console.error('Error loading statistics');
            });
    }

    function fetchDonors() {
        const bloodGroup = searchBloodGroup.value;
        const location = searchLocation.value;
        let url = '/api/blood-donors?';
        if (bloodGroup) url += `blood_group=${encodeURIComponent(bloodGroup)}&`;
        if (location) url += `location=${encodeURIComponent(location)}`;
        fetch(url)
            .then(res => res.json())
            .then(data => {
                renderDonors(data.donors || []);
            })
            .catch(() => {
                donorsContainer.innerHTML = '<p>Error loading donors.</p>';
            });
    }

    donorForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = {
            name: donorForm.name.value,
            blood_group: donorForm['blood-group'].value,
            location: donorForm.location.value,
            contact: donorForm.contact.value
        };
        fetch('/api/blood-donors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    donorForm.reset();
                    fetchDonors();
                    loadStatistics(); // Reload statistics after adding new donor
                    alert('Donor registered successfully!');
                } else {
                    alert(data.message || 'Registration failed.');
                }
            })
            .catch(() => alert('Error registering donor.'));
    });

    searchButton.addEventListener('click', function(e) {
        e.preventDefault();
        fetchDonors();
    });

    // Initial load
    fetchDonors();
    loadStatistics();
});