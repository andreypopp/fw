var player = (function() {

var currAudio, nextAudio;
var data = [];
var curr = 0;
var transitionTime = 3 * 1000; // sec
var playTime = 10 * 1000; // sec

function showPhoto(track) {
	//var trackTmpl = '<img src="{artistPhoto}"/>';
	//var result = trackTmpl.supplant(track);
	var image = document.createElement('img');
	var $nextPhoto = $('#nextPhoto');
	var wW = $(window).width();
	//console.log('wW:' + wW);
	var wH = $(window).height();
	//console.log('wH:' + wH);
	var size = (wW > wH) ? wW : wH;
	image.onload = function() {
		var orientation = (this.width > this.height) ? 'height="' + size + '"' : ' width="' + size + '"';
		$nextPhoto.html('<img class="bg" src="' + track.artistPhoto + '" ' + orientation + '/>').fadeIn(transitionTime, function() {
			$(this).show().attr('id', 'currPhoto');
		});
	};
	image.src = track.artistPhoto;

	$('#currPhoto').fadeOut(transitionTime, function() {
		$(this).hide().attr('id', 'nextPhoto');
	});
}

function showArtist(track) {
	$('#nextArtist').html(track.artistName).css('opacity', 0).show().animate({opacity: 0.75}, transitionTime, function() {
			$(this).show().attr('id', 'currArtist');
		});

	$('#currArtist').fadeOut(transitionTime, function() {
		$(this).hide().attr('id', 'nextArtist');
	});
}

function showInfo(track) {
	var trackTmpl = '<div class="friendPhoto {userPicOrientation}"><img src="{userPic}"/><div class="friendName">{userName}</div></div><div class="coverSrc"><img src="{coverSrc}"/></div><div class="artistName">{artistName}</div><div class="songName">{songName}</div>';
	var result = trackTmpl.supplant(track);
	$('#currTrack').fadeOut(transitionTime, function() {
		$(this).hide().attr('id', 'nextTrack');
	});
	$('#nextTrack').html(result).fadeIn(transitionTime, function() {
		$(this).show().attr('id', 'currTrack');
	});
}

function addToPlaylist(track) {
	//console.log(track.timestamp);
	var trackTmpl = '<div class="track"><div class="friendPhoto {userPicOrientation}"><img src="{userPic}"/><div class="friendName">{userName}</div></div><div class="coverSrc"><img src="{coverSrc}"/></div><div class="artistName">{artistName}</div><div class="songName">{songName}</div></div>';
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
	//console.log(data);
	nextTrack = data.shift();
	//console.log(nextTrack);
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
	showArtist(nextTrack);
	shiftPlaylist();

	// exchange currAudio and nextAudio
	var tmp = currAudio;
	currAudio = nextAudio;
	nextAudio = tmp;

	setTimeout(playNext, playTime - transitionTime);
}

var started = false;
var count = 0;

function addTrack(track) {
	track.userPic = 'https://graph.facebook.com/' + track.userId + '/picture?type=large';
	var image = document.createElement('img');
	image.onload = function() {
		count = count + 1;
		track.userPicOrientation = (this.width > this.height) ? 'horizontal' : 'vertical';
		data.push(track);
		if (!started && count > 1) {
			start();
			started = true;
		}
		addToPlaylist(track);
	};
	image.src = track.userPic;
}

function onError() {
	console.log('error');
}

function start() {
	//console.log('start');
	//console.log(data);
	nextTrack = data.shift();
	if (!nextTrack) { return; }

	currAudio = document.createElement("audio");
	//currAudio.controls = true;
	currAudio.onerror = onError;
	document.body.appendChild(currAudio);

	nextAudio = document.createElement("audio");
	//nextAudio.controls = true;
	nextAudio.onerror = onError;
	document.body.appendChild(nextAudio);

	currAudio.src = nextTrack.src;
	//console.log(nextTrack.songName + ' - ' + nextTrack.src);
	tools.fadeIn(currAudio, transitionTime);
	showInfo(nextTrack);
	showPhoto(nextTrack);
	showArtist(nextTrack);
	shiftPlaylist();

	loadNext();
	setTimeout(playNext, playTime - transitionTime);
}

return {
	addTrack: addTrack,
	start: start
};

}());