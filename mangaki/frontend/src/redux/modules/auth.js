import { createAction, handleActions } from 'redux-actions'
import axios from 'axios'

// Constants
export const REQUEST_AUTHENTICATION = 'REQUEST_AUTHENTICATION'
export const LOG_IN = 'LOG_IN'
export const LOGGED_IN = 'LOGGED_IN'
export const LOG_OUT = 'LOG_OUT'

const initialState = {
  isAuthenticated: false,
  authenticationRequested: false,
  username: null,
  token: null,
  tokenStart: null
}

// Actions
export const requestAuthentication = createAction(REQUEST_AUTHENTICATION)
export const logOut = createAction(LOG_OUT)
export const loggedIn = createAction(LOGGED_IN, token => ({token, start: Date.now()}))

/** FIXME: Check for shouldLogIn **/
/** FIXME: Setup an auto-refresh logIn to check if it is going to die **/
export const logIn = (username, password) => {
  return (dispatch, getState) => {
    dispatch(requestAuthentication(username))
    /** Let's get a JWT token **/
    return axios.post('/api/auth', {username, password})
    .then(resp => resp.data)
    .then(({token}) =>
      /** Got a token, logged in! **/
      dispatch(loggedIn(token))
    )
    .catch(error => {
      /** Error happened, bad credentials? **/
      console.log(`Something wrong with auth happened: ${error.message}`)
    })
  }
}

// Reducer
export default handleActions({
  [REQUEST_AUTHENTICATION]: (state, {payload}) => ({
    username: payload,
    authenticationRequest: true
  }),

  [LOG_OUT]: state => ({
    initialState
  }),

  [LOGGED_IN]: (state, {payload}) => ({
    isAuthenticated: true,
    authenticationRequested: false,
    token: payload.token,
    tokenStart: payload.start
  })
}, initialState)
