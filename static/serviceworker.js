// Listen for install event, set callback
self.addEventListener('install', function(event) {
    // Perform some task
});

self.addEventListener('activate', function(event) {
    // Perform some task
});


// needed to avoid 'Page does not work offline' error
self.addEventListener('fetch', function(event) {
    // Perform some task
});