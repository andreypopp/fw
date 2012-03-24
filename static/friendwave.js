(function() {
	window.friendWave = function (userId, accessToken) {
		var WebSocket = window.WebSocket || window.MozWebSocket;
		var connection = new WebSocket('ws://' + settings.waveEndpoint);
		connection.onopen = function () {
			console.log('connected');
    };

    connection.onerror = function (error) {
			console.log('error:', error);
    };

    connection.onmessage = function (message) {
			try {
				var json = JSON.parse(message.data);
			} catch (e) {
				console.log('error decoding data:', message.data);
				return;
			}
			console.log(json)
    };
	};
})();
