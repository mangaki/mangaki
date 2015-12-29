import React from 'react'
import Formsy from 'formsy-react'

import LoginForm from 'components/LoginForm'

export class LoginView extends React.Component {
  logIn (model) {
  }
  render () {
    return (
      <div className='container'>
        <div className='row'>
          <div className='page-header'>
            <h1>Se connecter</h1>
          </div>
          <Formsy.Form onSubmit={this.logIn} ref='form'>
            <LoginForm />
          </Formsy.Form>
        </div>
      </div>
    )
  }
}

export default LoginView
