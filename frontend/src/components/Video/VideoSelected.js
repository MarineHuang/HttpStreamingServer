import React from 'react';
import VideoDetail from '../Video/VideoDetail';
import './VideoSelected.css';


export default function VideoSelected({
    video, handleVideoSelect, setHistoryPager, authTokens,
    historyPager, seriesPager, seriesVideos, moviesPager, moviesVideos, isInitialVideoDone
}) {
    return (
        <div className="container-v1" >
            {/* 左侧栏 */}
            <div className="left-container">
                <div className="ui grid">
                    <div className="ui column">
                        <VideoDetail
                            video={video}
                            handleVideoSelect={handleVideoSelect}
                            setHistoryPager={setHistoryPager}
                            authTokens={authTokens}
                        />
                    </div>
                </div>
            </div>

            {/* 右侧栏 */}
            <div className="right-container">
                <h4>RECENTLY WATCHED</h4>
                <h4>MOVIES</h4>
            </div>
        </div>
            
            
    );
}
