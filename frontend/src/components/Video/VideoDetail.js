import React, {useEffect, useState, useRef} from 'react';
import { client } from '../../api/djangoAPI';
import Button from "@material-ui/core/Button";
import './VideoDetail.css'
//import SubtitleForm from "./SubtitlesForm"
//import dashjs from 'dashjs'
//import ResolutionSelector from './ResolutionSelector';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import 'videojs-contrib-dash';

function VideoDetail  ({ video, handleVideoSelect, authTokens, setHistoryPager }) {
    const videoRef = useRef(null);
    const playerRef = useRef(null);
    const [timer, setTimer] = useState(false);
    const [count, setCount] = useState(0);
    //const [player, setPlayer] = useState({});
    //const [playerIsInitialized, setPlayerIsInitialized] = useState(false);
    
    async function HandleNextEpisode(handleVideoSelect, nextEpisodeID) {
        const video = await client.getVideoById(nextEpisodeID);
        handleVideoSelect(video);
    }
    
    
    function startVideo() {
        setTimer(true); 
    }
    
    //function canPlay(video) {
    //    if (video.time > 0){
    //        player.seek(video.time);
    //    }
    //}

    // Dispose the Video.js player when the functional component unmounts
    useEffect(() => {
        const player = playerRef.current;

        return () => {
          if (player && !player.isDisposed()) {
            player.dispose();
            playerRef.current = null;
          }
        };
    }, [playerRef]);

    useEffect(() => {
        console.log('Video has changed.');
        if (video) {
            // Make sure Video.js player is only initialized once
            if (!playerRef.current) {
                console.log('playerRef is null')
                while (videoRef.current.firstChild) {
                    videoRef.current.removeChild(videoRef.current.lastChild);
                }

                const videoElement = document.createElement("video-js");
                videoElement.classList.add('vjs-big-play-centered');
                videoRef.current.appendChild(videoElement);
                
                const player = playerRef.current = videojs(videoElement, {
                    autoplay: false,
                    playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
                    controls: true,
                    responsive: true,
                    fluid: true,
                    controlBar: {
                        volumePanel: {
                            inline: false // makes volume-control VERTICAL
                        }
                    },
                    sources: {
                        src: video.videoUrl,
                        type: 'application/dash+xml'
                    }
                }, () => {
                    videojs.log('player is ready');
                    // add subtitles
                    videojs.log('add new subtitles when player is ready')
                    video.subtitles.map((sub, index) => {
                        var textTrack = {
                            tech: player.tech_,
                            kind: "subtitles",
                            label: sub.language,
                            srclang: sub.language,
                            src: sub.webvtt_subtitle_url,
                            default: true
                        };
                        player.addRemoteTextTrack(textTrack, true);
                    });
                });

            } else {
                const player = playerRef.current;
                // remove subtitles
                console.log('remove subtitle when video changed')
                var tracks = player.remoteTextTracks();
                if(tracks != null && tracks.tracks_ != null && tracks.tracks_.length > 0 ){
                    do{
                        player.removeRemoteTextTrack(tracks.tracks_[0]);
                    }while (tracks.tracks_.length > 0);
                };
                
                // add new source
                player.src({
                    src: video.videoUrl,
                    type: 'application/dash+xml'
                });

                // add new subtitles
                console.log('add subtitles when video changed')
                video.subtitles.map((sub, index) => {
                    var textTrack = {
                        tech: player.tech_,
                        kind: "subtitles",
                        label: sub.language,
                        srclang: sub.language,
                        src: sub.webvtt_subtitle_url,
                        default: true
                    };
                    player.addRemoteTextTrack(textTrack, true);
                });
            }
        }
    }, [video]);
    
    
    useEffect(() => {
        if(timer){
            const theThimer =
            setInterval(async () =>{
                setCount(count + 1);
                const player = playerRef.current;
                const newHistory =  await client.updateHistory (video.id, Math.round( player.time() ));
                setHistoryPager(newHistory);
            }, 20000);
            return () => {
                console.log('clear');
                clearInterval(theThimer);
            }
        }
    }, [timer, count]);
        
    
    if (!video) {
        return null;
    }


    return (
        <div>
            <div className="ui embed">
                <div ref={videoRef} />
            </div>
            <div className="ui segment">
                <h4 className="ui header">{video.name}</h4>
            </div>
            {/*<ResolutionSelector playerref={player} video={video} playerIsInitialized={playerIsInitialized}/>*/}
            <div className="ui segment">
                {video.nextEpisode &&
                    <Button  onClick={() => HandleNextEpisode(handleVideoSelect,video.nextEpisode)} variant="contained" color="primary">
                        Next Episode
                    </Button>
                }
            </div>
            <div className="hideifmobile">
            {/*authTokens && <SubtitleForm video={video} token={authTokens} />*/}
            </div>

        </div>
    );
};

export default VideoDetail;
