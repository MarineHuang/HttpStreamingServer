import axios from 'axios';

/**
 * initialize the client with the base url
 */
const http = axios.create({
    baseURL: process.env.REACT_APP_DJANGO_API,
    responseType: 'json'
})

const VIDEOS_ENDPOINT = '/videos';

/*******************************************
 **************** VIDEOS *******************
 *******************************************
 */

/**
 * performs GET request to retrieve a single video by it's ID
 *
 * @param id
 *          video's id
 * @returns {Promise<void>}
 *          videos list
 */
function getVideoById(id) {
    return http.get(`${VIDEOS_ENDPOINT}/${id}`, {transformResponse: [response => singleVideoMapper(response)]});
}

/**
 * performs GET request to retrieve videos list from searchbar entry
 * the param is optional, retrieve full video list instead if not provided
 * 
 * @param name 
 *          searchbar query, optional
 * @returns {Promise<void>}
 *          videos list
 */
function searchVideos(searchQuery) {
    const params = searchQuery ? {search_query: searchQuery} : null;
    return http.get(`${VIDEOS_ENDPOINT}/`, {params: params, transformResponse: [response => videosMapper(response)]});
}

/** 
 ******************************************
 **************** PAGER *******************
 ******************************************
 */

/**
 * performs GET request to retrieve the next videos in the list
 *
 * @param nextQuery
 *          the full query, usually : "/streaming/videos/?limit=xx&offset=xx"
 * @returns {Promise<void>}
 *          videos list
 */
function pagerNext(url) {
    return http.get(url, {transformResponse: [response => videosMapper(response)]});
}


/** 
 ******************************************
 **************** MAPPERS *****************
 ******************************************
 */

/**
 * Map videos list from response into standard object
 *
 * @param response
 *          expected response from api
 * @returns
 *          mapped object videos list
 */
function videosMapper(response) {
    const numberOfPages = Math.ceil(response.count / response.results.length);
    const videosPerPages = response.results.length;
    // use the singleVideoMapper for every videos
    const videos = response.results.map(video => singleVideoMapper(video));

    return {
        count: response.count,
        videos: videos,
        numberOfPages: numberOfPages,
        videosPerPages: videosPerPages, 
        nextQuery: response.next,
        previousQuery: response.previous
    }
}

/**
 * Map single video from response into standard object
 *
 * @param response
 *          expected response from api
 * @returns
 *          mapped object video
 */
function singleVideoMapper(response) {

    return {
        id: response.id,
        name: response.name,
        videoUrl: response.video_url,
        thumbnail: response.thumbnail,
        frSubtitleUrl: response.fr_subtitle_url,
        enSubtitleUrl: response.en_subtitle_url,
        ovSubtitleUrl: response.ov_subtitle_url
    }
}

/** 
 ******************************************
 **************** HANDLER *******************
 ******************************************
 */

/**
 * handle the errors coming from api
 *
 * @param err
 *          the full catched error
 */
function handleError(err) {
    if (err.response) {
        console.log(err.response.data);
    } else if (err.request) {
        console.log(err.request);
    } else {
        console.log('err', err.message);
    }
}

export {getVideoById, searchVideos, pagerNext, handleError}