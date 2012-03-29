/**
 * Audio fade in support
 */

var tools = {};

/**
 * Start audio playing with fade in period.
 * Equals to audio.play() but with smooth volume in.
 * @param {Object} audio HTML5 audio element
 * @param {Number} rampTime How long is the fade in ms
 */
tools.fadeIn = function(audio, rampTime) {
	// By default, ramp up in one second
	if (!rampTime) { rampTime = 1000; }

	var targetVolume = 1;
	var tick = 50; // How often adjust audio volume (ms)
	var volumeIncrease = targetVolume / (rampTime / tick);
	var playingEventHandler = null;

	function ramp() {
		var vol = Math.min(targetVolume, audio.volume + volumeIncrease);
		audio.volume = vol;

		// Have we reached target volume level yet?
		if (audio.volume < targetVolume) {
			// Keep up going until 11
			setTimeout(ramp, tick);
		}
	}

	function startRampUp() {
		// For now, we capture only the first playing event
		// as we assume the user calls fadeIn()
		// every time when wants to resume playback
		audio.removeEventListener("playing", playingEventHandler);
		ramp();
	}

	// Start with zero audio level
	audio.volume = 0;

	// Start volume ramp up when the audio actually stars to play (not when begins to buffer, etc.)
	audio.addEventListener("playing", startRampUp);
	
	if ((audio.buffered != undefined) && (audio.buffered.length != 0)) {
		var bb = parseInt(audio.buffered.end(0), 10);
		//console.log(bb);
		if (bb > 30) {
			audio.currentTime = 30;
		} else {
			audio.currentTime = bb;
		}
	}
	//audio.currentTime = 5; //jump to 30 sec
	audio.play();
};


/**
 * Stop audio playing with fade out period.
 * Equals to audio.pause() but with smooth volume out.
 * @param {Object} audio HTML5 audio element
 * @param {Number} rampTime How long is the fade in ms
 */
tools.fadeOut = function(audio, rampTime, callback) {
	// By default, ramp up in one second
	if (!rampTime) { rampTime = 1000; }

	var orignalVolume = audio.volume;
	var targetVolume = 0;
	var tick = 50; // How often adjust audio volume (ms)
	var volumeStep = (audio.volume - targetVolume) / (rampTime / tick);

	if (!volumeStep) {
		throw "Could not calculate volume adjustment step";
	}

	function ramp() {
		var vol = Math.max(0, audio.volume - volumeStep);
		audio.volume = vol;

		// Have we reached target volume level yet?
		if (audio.volume > targetVolume) {
			// Keep up going until 11
			setTimeout(ramp, tick);
		} else {
			audio.pause();

			// Reset audio volume so audio can be played again
			audio.volume = orignalVolume;

			if (typeof callback === 'function') {
				callback();
			}
		}
	}

	ramp();
};

String.prototype.supplant = function(o) {
    return this.replace(/{([^{}]*)}/g,
        function(a, b) {
            var r = o[b];
            return typeof r === 'string' || typeof r === 'number' ? r : a;
        }
    );
};

function getParameterByName(name) {
  name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
  var regexS = "[\\?&]" + name + "=([^&#]*)";
  var regex = new RegExp(regexS);
  var results = regex.exec(window.location.search);
  if(results == null)
    return "";
  else
    return decodeURIComponent(results[1].replace(/\+/g, " "));
}