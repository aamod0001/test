// Global Application State
let currentTab = 'find-blood';
let userLocation = { lat: 27.7007, lon: 85.3001 }; // Defaults to Kathmandu
let map = null;
let tileLayer = null;
let markersGroup = null;
let currentSearchMarker = null; // Temp marker for clicked coordinates
let activeBloodBanks = [];

// API Paths
const APIS = {
    search: (lat, lon, type) => `/getbloodbanks/${lat}/${lon}/${encodeURIComponent(type)}`,
    addBank: '/addBank',
    allBanks: '/api/bloodbanks',
    manageStock: (id) => `/api/bloodbanks/${id}/stock`,
    requests: '/api/bloodrequests',
    fulfillRequest: (id) => `/api/bloodrequests/${id}/fulfill`,
    stats: '/api/stats'
};

// Document Lifecycle Setup
document.addEventListener('DOMContentLoaded', () => {
    // 1. Detect location and initialize map
    detectLocation(() => {
        initMap();
        searchBlood();
    });

    // 2. Load analytics and side data
    loadStats();
    loadStockBankDropdown();
    loadUrgentRequests();

    // 3. Setup event listeners
    document.getElementById('btn-refresh-location').addEventListener('click', () => {
        detectLocation(() => {
            updateCoordsLabel();
            if (map) map.setView([userLocation.lat, userLocation.lon], 13);
            searchBlood();
        });
    });

    document.getElementById('btn-search-blood').addEventListener('click', searchBlood);
    document.getElementById('form-post-request').addEventListener('submit', handlePostRequest);
    document.getElementById('form-register-bank').addEventListener('submit', handleRegisterBank);
    document.getElementById('stock-bank-select').addEventListener('change', (e) => {
        loadStockEditor(e.target.value);
    });

    // 4. Setup Theme Toggle
    const themeBtn = document.getElementById('theme-toggle-btn');
    themeBtn.addEventListener('click', toggleTheme);
    
    // Load initial theme preference
    const savedTheme = localStorage.getItem('raktakosh-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme);
});

// Tab Switching Control
function switchTab(tabId) {
    currentTab = tabId;
    
    // Update navigation buttons active state
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`btn-${tabId}`);
    if (activeBtn) activeBtn.classList.add('active');

    // Update visibility of content sections
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    const activeContent = document.getElementById(`tab-${tabId}`);
    if (activeContent) activeContent.classList.add('active');

    // Update tab-specific titles/descriptions
    const titleEl = document.getElementById('current-tab-title');
    const descEl = document.getElementById('current-tab-desc');
    
    if (tabId === 'find-blood') {
        titleEl.textContent = 'Find Blood Banks';
        descEl.textContent = 'Search for blood banks near your location with active stock.';
    } else if (tabId === 'urgent-requests') {
        titleEl.textContent = 'Urgent Blood Requests';
        descEl.textContent = 'Help save a life. Browse urgent patient notices or post a new request.';
        loadUrgentRequests();
    } else if (tabId === 'manage-stock') {
        titleEl.textContent = 'Manage Stock Inventory';
        descEl.textContent = 'Admins can select a blood bank to update stock levels for different blood groups.';
        loadStockBankDropdown();
    } else if (tabId === 'register-bank') {
        titleEl.textContent = 'Register Blood Bank';
        descEl.textContent = 'Add a new blood bank to the search network. Use the map picker to get coordinates.';
    }
}

// Geolocation Handling
function detectLocation(callback) {
    const coordsLabel = document.getElementById('txt-coordinates');
    coordsLabel.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Getting GPS...`;

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                userLocation.lat = position.coords.latitude;
                userLocation.lon = position.coords.longitude;
                updateCoordsLabel();
                if (callback) callback();
            },
            (error) => {
                console.warn("Geolocation failed. Falling back to Kathmandu coordinates. Reason: " + error.message);
                // Fallback to Kathmandu coordinates
                userLocation.lat = 27.7007;
                userLocation.lon = 85.3001;
                coordsLabel.innerHTML = `<span class="coord-label">Using default (Kathmandu)</span>`;
                if (callback) callback();
            },
            { timeout: 6000 }
        );
    } else {
        coordsLabel.innerHTML = `GPS unsupported (Kathmandu default)`;
        if (callback) callback();
    }
}

function updateCoordsLabel() {
    const coordsLabel = document.getElementById('txt-coordinates');
    coordsLabel.innerHTML = `<span class="coord-detected"><i class="fa-solid fa-circle-check"></i> ${userLocation.lat.toFixed(4)}, ${userLocation.lon.toFixed(4)}</span>`;
}

// Leaflet Map Initialization
function initMap() {
    // Create map object
    map = L.map('map', {
        center: [userLocation.lat, userLocation.lon],
        zoom: 13,
        doubleClickZoom: false // Disable double click zoom to support coordinates picking
    });

    markersGroup = L.layerGroup().addTo(map);

    // Initial tile layer loading based on theme
    const theme = document.documentElement.getAttribute('data-theme') || 'dark';
    setMapTiles(theme);

    // Add a marker for the user's current search location
    L.circle([userLocation.lat, userLocation.lon], {
        color: 'var(--red-primary)',
        fillColor: 'var(--red-primary)',
        fillOpacity: 0.15,
        radius: 1200
    }).addTo(map);

    L.marker([userLocation.lat, userLocation.lon], {
        icon: L.divIcon({
            html: `<div style="background-color: var(--blue-primary); border: 2px solid white; border-radius: 50%; width: 14px; height: 14px; box-shadow: 0 0 10px rgba(0,0,0,0.5)"></div>`,
            className: 'user-gps-marker',
            iconSize: [14, 14]
        })
    }).addTo(map).bindPopup("Your Location");

    // Double click map listener to pick coordinates for registering blood banks
    map.on('dblclick', (e) => {
        const { lat, lng } = e.latlng;
        
        // Show temp marker on map
        if (currentSearchMarker) {
            currentSearchMarker.setLatLng(e.latlng);
        } else {
            currentSearchMarker = L.marker(e.latlng, {
                icon: L.divIcon({
                    html: `<i class="fa-solid fa-location-dot" style="font-size: 26px; color: var(--orange-primary); filter: drop-shadow(0 2px 5px rgba(0,0,0,0.5))"></i>`,
                    className: 'temp-marker',
                    iconSize: [26, 26],
                    iconAnchor: [13, 26]
                })
            }).addTo(map);
        }
        currentSearchMarker.bindPopup(`Selected coordinates:<br>Lat: ${lat.toFixed(6)}<br>Lng: ${lng.toFixed(6)}`).openPopup();

        // If user is on the register-bank tab, autofill form coordinates
        if (currentTab === 'register-bank') {
            document.getElementById('reg-latitude').value = lat.toFixed(6);
            document.getElementById('reg-longitude').value = lng.toFixed(6);
            
            // Subtle flash animation on inputs to guide the user
            document.getElementById('reg-latitude').style.borderColor = 'var(--orange-primary)';
            document.getElementById('reg-longitude').style.borderColor = 'var(--orange-primary)';
            setTimeout(() => {
                document.getElementById('reg-latitude').style.borderColor = '';
                document.getElementById('reg-longitude').style.borderColor = '';
            }, 1000);
        } else {
            // Suggest going to Register Bank Tab
            const badge = document.getElementById('map-interaction-status');
            badge.textContent = `Coordinates picked! Switch to "Register Bank" to add it.`;
            badge.style.color = 'var(--orange-primary)';
            setTimeout(() => {
                badge.textContent = `Double-click map to copy coordinates`;
                badge.style.color = '';
            }, 5000);
        }
    });
}

// Swap Map Tile Layer styles (CartoDB voyager vs CartoDB dark matter)
function setMapTiles(theme) {
    if (tileLayer) {
        map.removeLayer(tileLayer);
    }
    
    let tileUrl = '';
    let attribution = '';
    
    if (theme === 'dark') {
        tileUrl = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
        attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
    } else {
        tileUrl = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
        attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
    }

    tileLayer = L.tileLayer(tileUrl, {
        attribution: attribution,
        maxZoom: 20
    }).addTo(map);
}

// Fetch stats analytics
function loadStats() {
    fetch(APIS.stats)
        .then(res => res.json())
        .then(data => {
            document.getElementById('stat-total-banks').textContent = data.totalBanks;
            document.getElementById('stat-active-requests').textContent = data.activeRequests;
            document.getElementById('stat-total-pints').textContent = data.totalBloodPints;
            
            // Update request side tab count badge
            const badge = document.getElementById('badge-requests-count');
            badge.textContent = data.activeRequests;
            badge.style.display = data.activeRequests > 0 ? 'inline-block' : 'none';
        })
        .catch(err => console.error("Error loading stats: ", err));
}

// Proximity Blood Bank Search
function searchBlood() {
    const bloodType = document.getElementById('search-blood-type').value;
    const listContainer = document.getElementById('blood-banks-list');
    
    listContainer.innerHTML = `
        <div class="loading-state">
            <i class="fa-solid fa-circle-notch fa-spin"></i> Finding nearest banks with ${bloodType} stock...
        </div>
    `;

    // Clear map markers
    if (markersGroup) markersGroup.clearLayers();

    fetch(APIS.search(userLocation.lat, userLocation.lon, bloodType))
        .then(res => res.json())
        .then(banks => {
            activeBloodBanks = banks;
            listContainer.innerHTML = '';

            if (banks.length === 0) {
                listContainer.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-hospital-slash" style="font-size: 24px; margin-bottom: 8px;"></i>
                        No blood banks within search radius hold active stock for <strong>${bloodType}</strong>.
                    </div>
                `;
                return;
            }

            // Bind each bank to list & map marker
            banks.forEach((bank, idx) => {
                // Calculate distance in kilometers using Spherical Law of Cosines
                const distance = calcDistance(userLocation.lat, userLocation.lon, bank.latitude, bank.longitude);
                
                // Add list Card
                const card = document.createElement('div');
                card.className = 'bank-card';
                card.id = `bank-card-${bank.bloodBankId}`;
                card.addEventListener('click', () => highlightBloodBank(bank));

                const imageUrl = bank.imageUrl || 'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=400';

                card.innerHTML = `
                    <img src="${imageUrl}" class="bank-img" alt="${bank.name}">
                    <div class="bank-info">
                        <div>
                            <h4 class="bank-name">${bank.name}</h4>
                            <div class="bank-detail-item"><i class="fa-solid fa-map-marker-alt"></i> ${bank.address || 'Address unspecified'}</div>
                            <div class="bank-detail-item"><i class="fa-solid fa-phone"></i> ${bank.contact || 'Phone unspecified'}</div>
                        </div>
                        <div>
                            <span class="dist-badge"><i class="fa-solid fa-road"></i> ${distance.toFixed(1)} km away</span>
                        </div>
                    </div>
                    <div class="stock-badge-container">
                        <span class="stock-badge">${bank.quantity} Pints</span>
                    </div>
                `;
                listContainer.appendChild(card);

                // Add Custom Map Marker
                const markerIcon = L.divIcon({
                    html: `
                        <div class="marker-pin-wrapper">
                            <span class="marker-inner-text">${bloodType}</span>
                        </div>
                    `,
                    className: 'custom-map-marker',
                    iconSize: [36, 36],
                    iconAnchor: [18, 36]
                });

                const marker = L.marker([bank.latitude, bank.longitude], { icon: markerIcon })
                    .addTo(markersGroup)
                    .bindPopup(`
                        <div class="map-popup-card">
                            <h4>${bank.name}</h4>
                            <p><i class="fa-solid fa-location-dot"></i> ${bank.address || 'Address unspecified'}</p>
                            <p><i class="fa-solid fa-phone"></i> ${bank.contact || 'Phone unspecified'}</p>
                            <div class="map-popup-stock">
                                <span>${bloodType} Available</span>
                                <span class="stock-badge">${bank.quantity} Pints</span>
                            </div>
                            <a href="tel:${bank.contact}" style="display: block; margin-top: 8px; font-size: 11px; text-decoration: none; color: var(--red-primary); font-weight: 600;">
                                <i class="fa-solid fa-phone-flip"></i> Place Order Request
                            </a>
                        </div>
                    `);

                // Store leaflet marker reference on bank object for card-click centering
                bank.leafletMarker = marker;
            });

            // Adjust map view to fit all markers
            if (banks.length > 0 && map) {
                const group = new L.featureGroup(banks.map(b => b.leafletMarker));
                map.fitBounds(group.getBounds().pad(0.15));
            }
        })
        .catch(err => {
            console.error(err);
            listContainer.innerHTML = `
                <div class="empty-state text-red">
                    <i class="fa-solid fa-triangle-exclamation"></i> Error loading search records. Please retry.
                </div>
            `;
        });
}

// Center map and focus on selected blood bank card
function highlightBloodBank(bank) {
    document.querySelectorAll('.bank-card').forEach(c => c.classList.remove('highlighted'));
    const card = document.getElementById(`bank-card-${bank.bloodBankId}`);
    if (card) {
        card.classList.add('highlighted');
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    if (map && bank.leafletMarker) {
        map.setView([bank.latitude, bank.longitude], 15);
        bank.leafletMarker.openPopup();
    }
}

// Calculate distance in kilometers
function calcDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // radius of Earth in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Load Blood Bank options into stock management dropdown
function loadStockBankDropdown() {
    const dropdown = document.getElementById('stock-bank-select');
    
    fetch(APIS.allBanks)
        .then(res => res.json())
        .then(banks => {
            dropdown.innerHTML = '<option value="" disabled selected>-- Select a Blood Bank --</option>';
            banks.forEach(bank => {
                const opt = document.createElement('option');
                opt.value = bank.bloodBankId;
                opt.textContent = bank.name;
                dropdown.appendChild(opt);
            });
            
            // Keep selection if previously selected
            if (selectedBankForStockId) {
                dropdown.value = selectedBankForStockId;
                loadStockEditor(selectedBankForStockId);
            }
        })
        .catch(err => console.error("Dropdown error: ", err));
}

// Render dynamic stock inventory input rows
function loadStockEditor(bankId) {
    selectedBankForStockId = bankId;
    const grid = document.getElementById('stock-editor-grid');
    grid.innerHTML = `<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> Fetching stock quantities...</div>`;

    fetch(APIS.manageStock(bankId))
        .then(res => res.json())
        .then(stocks => {
            grid.innerHTML = '';
            
            // Standard Nepalese blood types
            const standardTypes = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"];
            
            // Map fetched stock quantities
            const quantities = {};
            stocks.forEach(s => {
                quantities[s.type] = s.quantity;
            });

            standardTypes.forEach(type => {
                const qty = quantities[type] || 0;
                
                const row = document.createElement('div');
                row.className = 'stock-editor-row';
                row.innerHTML = `
                    <span class="stock-type-label"><i class="fa-solid fa-droplet"></i> ${type}</span>
                    <div class="stock-input-wrapper">
                        <input type="number" id="input-stock-${type}" class="form-input stock-input" min="0" value="${qty}">
                        <button class="primary-btn" style="padding: 8px 12px; box-shadow: none;" onclick="updateStockLevel('${bankId}', '${type}')" title="Save Stock">
                            <i class="fa-solid fa-floppy-disk"></i>
                        </button>
                    </div>
                `;
                grid.appendChild(row);
            });
        })
        .catch(err => {
            console.error(err);
            grid.innerHTML = `<div class="empty-state text-red">Failed to load inventory stock.</div>`;
        });
}

// POST stock updates
function updateStockLevel(bankId, type) {
    const input = document.getElementById(`input-stock-${type}`);
    const quantity = parseInt(input.value);

    if (isNaN(quantity) || quantity < 0) {
        alert("Quantity must be a positive integer.");
        return;
    }

    fetch(APIS.manageStock(bankId), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ type, quantity })
    })
    .then(res => {
        if (!res.ok) throw new Error("Update failed");
        return res.json();
    })
    .then(data => {
        // Visual indicator of successful save
        input.style.borderColor = 'var(--green-primary)';
        setTimeout(() => {
            input.style.borderColor = '';
        }, 1000);
        
        loadStats(); // Refresh dashboard pints numbers
        if (currentTab === 'find-blood') searchBlood();
    })
    .catch(err => {
        alert("Could not update blood stock inventory levels.");
        console.error(err);
    });
}

// Load Urgent Blood Requests Board
function loadUrgentRequests() {
    const list = document.getElementById('blood-requests-list');
    list.innerHTML = `<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading notices...</div>`;

    fetch(APIS.requests)
        .then(res => res.json())
        .then(requests => {
            list.innerHTML = '';
            if (requests.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-circle-check" style="font-size: 24px; color: var(--green-primary); margin-bottom: 8px;"></i>
                        No active urgent requests. The supply index is stable!
                    </div>
                `;
                return;
            }

            requests.forEach(req => {
                const card = document.createElement('div');
                card.className = 'request-card';
                card.innerHTML = `
                    <div class="request-card-header">
                        <div class="request-meta">
                            <h4>${req.patientName}</h4>
                            <span>Posted: ${new Date(req.createdAt).toLocaleDateString()}</span>
                        </div>
                        <span class="urgency-badge ${req.urgencyLevel.toLowerCase()}">${req.urgencyLevel}</span>
                    </div>
                    <div class="request-card-details">
                        <div class="request-detail-item"><i class="fa-solid fa-droplet text-red"></i> Needed: <span class="request-blood-badge">${req.bloodType}</span> (${req.quantity} Pints)</div>
                        <div class="request-detail-item"><i class="fa-solid fa-hospital-user"></i> Hospital: ${req.hospitalName}</div>
                        <div class="request-detail-item"><i class="fa-solid fa-phone"></i> Contact: ${req.contactNumber}</div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <a href="tel:${req.contactNumber}" class="secondary-btn" style="flex: 1; text-align: center; text-decoration: none; font-size: 13px;">
                            <i class="fa-solid fa-phone"></i> Call Donor Contact
                        </a>
                        <button class="primary-btn" style="padding: 8px 12px; box-shadow: none;" onclick="fulfillRequest('${req.requestId}')">
                            <i class="fa-solid fa-check"></i> Fulfill
                        </button>
                    </div>
                `;
                list.appendChild(card);
            });
        })
        .catch(err => {
            console.error(err);
            list.innerHTML = `<div class="empty-state text-red">Failed to load urgent requests.</div>`;
        });
}

// POST Fulfill Request
function fulfillRequest(requestId) {
    if (!confirm("Are you sure this blood request is fulfilled? This will remove the card from the noticeboard.")) return;

    fetch(APIS.fulfillRequest(requestId), {
        method: 'POST'
    })
    .then(res => {
        if (!res.ok) throw new Error("Fulfillment failed");
        return res.json();
    })
    .then(() => {
        loadUrgentRequests();
        loadStats();
    })
    .catch(err => {
        alert("Failed to mark request as fulfilled.");
        console.error(err);
    });
}

// POST a new urgent request
function handlePostRequest(e) {
    e.preventDefault();

    const payload = {
        patientName: document.getElementById('req-patient-name').value,
        bloodType: document.getElementById('req-blood-type').value,
        quantity: parseInt(document.getElementById('req-quantity').value),
        urgencyLevel: document.getElementById('req-urgency').value,
        hospitalName: document.getElementById('req-hospital').value,
        contactNumber: document.getElementById('req-contact').value
    };

    fetch(APIS.requests, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(res => {
        if (!res.ok) throw new Error("Request post failed");
        return res.json();
    })
    .then(() => {
        document.getElementById('form-post-request').reset();
        loadUrgentRequests();
        loadStats();
        alert("Urgent blood request posted successfully. It is now visible on the public noticeboard!");
    })
    .catch(err => {
        alert("Could not submit request. Check inputs and try again.");
        console.error(err);
    });
}

// POST a new blood bank registration
function handleRegisterBank(e) {
    e.preventDefault();

    const payload = {
        name: document.getElementById('reg-name').value,
        latitude: parseFloat(document.getElementById('reg-latitude').value),
        longitude: parseFloat(document.getElementById('reg-longitude').value),
        address: document.getElementById('reg-address').value,
        contact: document.getElementById('reg-contact').value,
        imageUrl: document.getElementById('reg-image-url').value
    };

    fetch(APIS.addBank, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(res => {
        if (!res.ok) throw new Error("Registration failed");
        return res.json();
    })
    .then(newBank => {
        document.getElementById('form-register-bank').reset();
        
        // Remove temp marker
        if (currentSearchMarker) {
            map.removeLayer(currentSearchMarker);
            currentSearchMarker = null;
        }

        // Re-focus map on new bank
        if (map) {
            map.setView([newBank.latitude, newBank.longitude], 14);
            L.marker([newBank.latitude, newBank.longitude]).addTo(markersGroup)
                .bindPopup(`<strong>${newBank.name}</strong><br>${newBank.address}`).openPopup();
        }

        loadStats();
        loadStockBankDropdown();
        
        alert("New blood bank successfully registered onto the network!");
        switchTab('find-blood');
        searchBlood();
    })
    .catch(err => {
        alert("Failed to register blood bank. Verify parameters are correct.");
        console.error(err);
    });
}

// Theme management (toggle dark/light)
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('raktakosh-theme', newTheme);
    
    updateThemeUI(newTheme);
    setMapTiles(newTheme);
}

function updateThemeUI(theme) {
    const btnText = document.getElementById('theme-btn-text');
    if (theme === 'dark') {
        btnText.textContent = "Light Mode";
    } else {
        btnText.textContent = "Dark Mode";
    }
}
