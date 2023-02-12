import React, { Component } from 'react';
//import Slider from "react-slick";
//import SampleNextArrow from "./SampleNextArrow";
//import SamplePrevArrow from "./SamplePrevArrow";
import './VideoList.css';


export default  class VideoList extends Component {

    //this variable must be the same as PAGE_SIZE in settings.py
    SLIDES_OF_CAROUSEL = 5;

    constructor(props) {
        super(props);
        this.state = {
            pager: this.props.pager,
            videos: this.props.videos
        };
        this.afterChangeMethod = this.afterChangeMethod.bind(this);
    };



    componentWillReceiveProps(nextProps) {
        const chooseIndex = (reset) =>{
            if(reset === true){
               return this.state.index;
            }
            return 0;
        };
        if (nextProps.videos !== this.props.videos) {
            const index = chooseIndex(nextProps.reset);
            this.setState({
                pager: nextProps.pager,
                videos: nextProps.videos
            });
        }
    };


    /**
     * this method is called by react slick after the slider finish transition
     * used to compute if we need to make new API calls
     * @param index
     * @returns {Promise<void>}
     */
    async afterChangeMethod(index) {
        const setSeriePagerIndex = (index) =>{
            if(this.state.pager.type === 'Serie'){
                this.setState({
                    index: index
                });
            }
        };
        const isLastPage = (index + this.SLIDES_OF_CAROUSEL) === this.state.videos.length;
        setSeriePagerIndex(index);
        if (isLastPage && this.state.pager.nextPageUrl){
            // API call to retrieve more videos when navigating through carousel
            try {
                let pager = this.state.pager;
                await pager.getNextPage();
                let videos = this.state.videos;
                videos.push(...pager.videos);
                this.setState({
                    pager: pager,
                    videos: videos
                });
            } catch(error) {
                console.log(error);
            }
        }
    };

    render() {
        const renderVideos = this.state.videos.map((video) => {
            return (
            <div className="video-list-item" 
                onClick={() => this.props.handleVideoSelect(video)}>
                <img className="img-cover" src={video.thumbnail}/>
                <div className="video-block-info">{video.name}</div>
            </div>);
        });
        
        return (
        <div>
            <div className="video-list-box">
                {renderVideos}
            </div>
        </div>
        );
    }
}

