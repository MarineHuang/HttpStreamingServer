import React, { Component } from 'react';
//import Slider from "react-slick";
//import SampleNextArrow from "./SampleNextArrow";
//import SamplePrevArrow from "./SamplePrevArrow";
import InfiniteScroll from 'react-infinite-scroller'
import './VideoList.css';


export default  class VideoList extends Component {

    //this variable must be the same as PAGE_SIZE in settings.py
    //SLIDES_OF_CAROUSEL = 5;

    constructor(props) {
        super(props);
        this.state = {
            hasMore: true,
            pager: this.props.pager,
            videos: this.props.videos
        };
        //this.loadMoreData = this.loadMoreData.bind(this);
    };


    // 加载更多数据
    async loadMoreData(){
        let pager = this.state.pager;
        if( !pager.nextPageUrl ) {
            this.setState({hasMore: false})
            console.log("has no more data")
            return
        }
        // API call to retrieve more videos
        try {
            console.log("loading more data: " + pager.nextPageUrl);
            await pager.getNextPage();
            let videos = this.state.videos;
            videos.push(...pager.videos);
            this.setState({
                pager: pager,
                videos: videos
            });
        } catch(error) {
            this.setState({hasMore: false})
            console.log(error);
        }
    }


    render() {
        const { hasMore } = this.state

        const renderVideos = this.state.videos.map((video) => {
            return (
            <div className="video-list-item" 
                onClick={() => this.props.handleVideoSelect(video)}
                key={video.id}>
                <img className="img-cover" src={video.thumbnail}/>
                <div className="video-block-info">{video.name}</div>
            </div>);
        });
        
        return (
        <div className="infinite-scroll-container">
                <InfiniteScroll
                    pageStart={0} // 设置初始化请求的页数
                    loadMore={()=>this.loadMoreData()}  // 监听的ajax请求
                    hasMore={hasMore} // 是否继续监听滚动事件 true 监听 | false 不再监听
                    initialLoad={false}
                    className="video-list-box"
                    //loader={<h4>Loading...</h4>}
                    //endMessage={<p style={{ textAlign: 'center' }}><b>No more videos</b></p>}
                >
                    {renderVideos}
                </InfiniteScroll>
        </div>
        );
    }
}

