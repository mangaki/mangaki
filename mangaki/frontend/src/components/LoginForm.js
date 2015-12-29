import React from 'react'
import { Input, Row } from 'formsy-react-components'

export class LoginForm extends React.Component {
  render () {
    const sharedProps = {
      layout: 'horizontal'
    }

    return (
      <div>
        <Input
          {...sharedProps}
          name='username'
          type='text'
          label="Votre nom d'utilisateur"
          required
        />
        <Input
          {...sharedProps}
          name='password'
          type='password'
          label='Votre mot de passe'
          required
        />
        <Row layout='horizontal'>
          <input className='btn btn-primary' formNoValidate={true} type='submit' defaultValue='Connexion' />
        </Row>
      </div>
    )
  }
}

export default LoginForm
