var player = (function() {

var currAudio, nextAudio;
var data = [];
var curr = 0;
var transitionTime = 5 * 1000; // sec
var playTime = 20 * 1000; // sec

function showPhoto(track) {
	var trackTmpl = '<img src="{artistPhoto}"/>';
	var result = trackTmpl.supplant(track);
	$('#currPhoto').fadeOut(transitionTime, function() {
		$(this).hide().attr('id', 'nextPhoto');
	});
	$('#nextPhoto').html(result).fadeIn(transitionTime, function() {
		$(this).show().attr('id', 'currPhoto');
	});
}

function showInfo(track) {
	var trackTmpl = '<div class="friendPhoto"><img src="https://graph.facebook.com/{userId}/picture?type=large"/><div class="friendName">{userName}</div></div><div class="coverSrc"><img src="{coverSrc}"/></div><div class="songName">{songName}</div><div class="artistName">by {artistName}</div>';
	var result = trackTmpl.supplant(track);
	$('#currTrack').fadeOut(transitionTime, function() {
		$(this).hide().attr('id', 'nextTrack');
	});
	$('#nextTrack').html(result).fadeIn(transitionTime, function() {
		$(this).show().attr('id', 'currTrack');
	});
}

function addToPlaylist(track) {
	console.log(track.songName);
	var trackTmpl = '<div class="track"><div class="friendPhoto"><img src="https://graph.facebook.com/{userId}/picture?type=large"/><div class="friendName">{userName}</div></div><div class="coverSrc"><img src="{coverSrc}"/></div><div class="songName">{songName}</div><div class="artistName">{artistName}</div></div>';
	var result = trackTmpl.supplant(track);
	$('#playlist').append(result);
}

function shiftPlaylist() {
	$('#playlist .track:eq(0)').animate({opacity: 0}, transitionTime, function(){
		$(this).html('<br/>').animate({width: 0}, 250, function() {
			$(this).remove();
		});
	});
}

function loadNext() {
	nextTrack = data.shift();
	if (nextTrack) {
		nextAudio.src = nextTrack.src;
		//console.log(nextTrack.songName + ' - ' + nextTrack.src);
	}
}

function playNext() {
	if (!nextTrack) {
		tools.fadeOut(currAudio, transitionTime); // if there's no next track, then just fade out the current one
		return;
	}

	tools.fadeOut(currAudio, transitionTime, loadNext); // fade out current track
	tools.fadeIn(nextAudio, transitionTime); // fade in next track
	showInfo(nextTrack);
	showPhoto(nextTrack);
	shiftPlaylist();

	// exchange currAudio and nextAudio
	var tmp = currAudio;
	currAudio = nextAudio;
	nextAudio = tmp;

	setTimeout(playNext, playTime - transitionTime);
}

function addTrack(track) {
	data.push(track);
	addToPlaylist(track);
}

function start() {
	nextTrack = data.shift();
	if (!nextTrack) { return; }

	currAudio = document.createElement("audio");
	//currAudio.controls = true;
	document.body.appendChild(currAudio);

	nextAudio = document.createElement("audio");
	//nextAudio.controls = true;
	document.body.appendChild(nextAudio);

	currAudio.src = nextTrack.src;
	//console.log(nextTrack.songName + ' - ' + nextTrack.src);
	tools.fadeIn(currAudio, transitionTime);
	showInfo(nextTrack);
	showPhoto(nextTrack);
	shiftPlaylist();

	loadNext();
	setTimeout(playNext, playTime - transitionTime);
}

return {
	addTrack: addTrack,
	start: start
};

}());