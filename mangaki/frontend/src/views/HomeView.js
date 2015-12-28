import React from 'react'

import _ from 'lodash'

export class HomeView extends React.Component {
  renderStudentCup () {
    return (
      <div>
        <p>
          Bon ben… on a gagné la Student Demo Cup. <a href='http://meta.mangaki.fr/t/mangaki-remporte-la-student-demo-cup-categorie-enterprise/605' target='_blank'>Discutez-en sur le forum !</a>
        </p>
        <blockquote className='twitter-tweet' lang='fr'>
          <p lang='fr' dir='ltr'>
            Le prix <a href='https://twitter.com/hashtag/enterprise?src=hash'>#entreprise</a> revient à <a href='https://twitter.com/MangakiFR'>@MangakiFR</a> !!! Félicitation et bravo à ts les autres pr vos sujets projets <a href='"https://twitter.com/hashtag/OSSPARIS15?src=hash'>#OSSPARIS15</a> <a href='https://t.co/PPnd5yjx9N'>pic.twitter.com/PPnd5yjx9N</a>
          </p>
          &mdash; Open Source Summit (@OSS_Paris) <a href='https://twitter.com/OSS_Paris/status/667035729223131136'>18 Novembre 2015</a>
        </blockquote>
      </div>
    )
  }

  renderActions () {
    const links = {
      '/about/': 'En savoir plus',
      '/user/signup/': 'S\'inscrire'
    }

    return (
      <div>
        {_.map(links, (text, href) => {
          return (
            <div className='col-md-4 col-sm-12 margin'>
              <a className='btn btn-mangaki btn-lg' href={href}>{text}</a>
            </div>
          )
        })}
        <div className='col-md-4 col-sm-12 margin'>
          <a className='btn btn-mangaki btn-lg' href='//github.com/mangaki/mangaki' target='_blank'>Voir sur GitHub</a>
        </div>
      </div>
    )
  }

  renderSponsors () {
    /** FIXME: Let's think about how we are going to implement them. **/
    return null
  }

  render () {
    return (
      <div>
        <div className='row'>
          <div className='col-md-6 col-sm-12'>
            {this.renderStudentCup()}
          </div>
          <div className='col-md-6 col-sm-12'>
            <div className='row'>
              {this.renderActions()}
            </div>
            <div className='row text-center'>
              <div className='col-md-12 col-sm-12 margin'>
                <img src={require('static/img/help.jpg')} />
              </div>
            </div>
          </div>
        </div>
        {this.renderSponsors()}
      </div>
    )
  }
}

export default HomeView
