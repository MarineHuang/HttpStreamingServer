
import React, {useEffect, useState} from 'react';
import { client } from '../../api/djangoAPI';

import VTTConverter from 'srt-webvtt';


function SubtitleForm ({video, token}){

    const [selectedFiles, setSelectedFiles] = useState(undefined);
    const [subtitleName, setSubtitleName] = useState("Custom Subtitle");

    const handleSubtitleChange = event => {
        let customsub = event.target.value;
        var ext = customsub.substr(customsub.lastIndexOf('.') + 1);
        if(ext != "srt"){
            alert("Only .srt files are supported \n");
            return;
        }
        const vttConverter = new VTTConverter(event.target.files[0]);
        let track = document.createElement("track");
        track.id= "my-sub-track";
        track.kind = "captions";
        track.label = subtitleName;
        let videoElement = document.getElementById("myVideo");
        videoElement.appendChild(track);
        vttConverter
        .getURL()
        .then(function(url) { // Its a valid url that can be used further
          track.src = url; // Set the converted URL to track's source
          videoElement.textTracks[0].mode = 'show'; // Start showing subtitle to your track
        })
        .catch(function(err) {
          alert(err);
        })
        setSelectedFiles(event.target.files);    
    };

    const handleSubtitleNameChange = event => {
        setSubtitleName(event.target.value);    
    };

    const handleSubmit = event => {
        event.preventDefault()  
        //console.log("coucou");
        console.log(selectedFiles[0]);
        //console.log(token.key);
        //console.log(video);
        client.uploadSubtitles(token.key, video.id, 'eng', selectedFiles[0]);
    };

    return (
            <div className="ui segment">
            <form  onSubmit={handleSubmit} >
                <label>
                Add Custom subtitles:
                <input type="file" onChange={handleSubtitleChange} />
                <input type="text" defaultValue="Custom Subtitle" onChange={handleSubtitleNameChange}/>
                <button onChange={handleSubmit} type="submit">Send </button>
                </label>
            </form>
        </div>
    )
}

export default SubtitleForm;

