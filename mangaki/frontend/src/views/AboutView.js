import React from 'react'
import Gravatar from 'react-gravatar'

import _ from 'lodash'

import styles from './AboutView.scss'

export class AboutView extends React.Component {
  renderTitle (title) {
    return (
      <h1 className={styles['about__title']}>{title}</h1>
    )
  }

  renderHeader () {
    return (
      <div>
        {this.renderTitle('Mangaki, la recommandation d\'anime et manga')}
        <figure className={styles['about__logo']}>
          <img src={require('static/img/chiro.png')} alt='Chiro' height={128} />
        </figure>

        <p>
          Mangaki a été créé par 3 passionnés qui cherchaient un moyen efficace de choisir leur prochaines séries d'<em>anime</em>/manga.
        </p>

        <p>
          À partir des séries que vous avez vues ou lues, il trouve celles qui sont le plus susceptibles de vous plaire et vous les conseille !
        </p>

        <p>
          Notre objectif est de rassembler les fans francophones d’anime et de manga autour d’une passion commune, et de leur permettre de la partager avec le reste de la communauté en partageant leurs avis, commentaires, conseils…
        </p>

        <p>
          Si vous souhaitez participer au projet, nous en serons ravis ! Vous pouvez déjà discuter sur <a href='http://meta.mangaki.fr' target='_blank'>le forum</a> et proposer des améliorations de la base de données. Si vous voulez vous investir davantage (développement, communication, etc.), écrivez-nous à <a href='mailto:info@mangaki.fr'>info@mangaki.fr</a>, et nous vous trouverons de quoi faire sans souci ;)
        </p>
      </div>
    )
  }

  renderPerformer (data) {
    /** FIXME: the data.realname is not correctly positioned, why? **/
    return (
      <div>
        <aside className={styles['about__performer']}>
          {data.performer}
        </aside>
        <h2>{data.pseudo}</h2>
        <span>{data.realname}</span>
        <h3>{data.title}</h3>
        <hr />
        {_.map(data.infos, info => {
          return (
            <p
              key={info}
              className={styles['about__infos']}
            >
              {info}
            </p>
          )
        })}
      </div>
    )
  }

  renderContributor (data) {
    return (
      <p><strong>{data.realname}</strong>{' '}{data.whathedoes}</p>
    )
  }

  renderTeam () {
    const lily = {
      performer: (
        <a href='https://www.facebook.com/leslueursdelily'>
          <img src={require('static/img/lily.png')} alt='Lily' />
        </a>
      ),
      pseudo: 'Lily',
      realname: 'Camille Laïly',
      title: 'Présidente',
      infos: [
        'Passionnée de japanimation et de musique, elle a créé Mangaki pour son projet de fin d’études des Mines de Paris ; elle s’occupe de la gestion, communication et partenariats du projet.',
        'À part ça, elle est chanteuse, rousse et fanatique de l\'anime Mushishi, dont elle vous parlera pendant des jours si vous la laissez faire.'
      ]
    }

    const jj = {
      performer: (
        <a href='https://www.youtube.com/user/Xnihpsel'>
          <Gravatar email='vie@jill-jenn.net' />
        </a>
      ),
      pseudo: 'JJ',
      realname: 'Jill-Jênn Vie',
      title: 'Développeur',
      infos: [
        'Il fait une thèse d’apprentissage statistique à l’université Paris-Saclay. Il a conçu l’algorithme de recommandation et s’occupe des aspects techniques du site.',
        'Fan absolu de Yoko Kanno, il regrettera à jamais la disparition de Satoshi Kon.'
      ]
    }

    const sedeto = {
      performer: (
        <a href='http://sedeto.fr'>
          <img src={require('static/img/sedeto.png')} alt='Sedeto' />
        </a>
      ),
      pseudo: 'Sedeto',
      realname: 'Solène Pichereau',
      title: 'Directrice artistique',
      infos: [
        'Elle travaille en tant que graphiste manga pour le Groupe Delcourt. C’est elle qui a réalisé le logo et la communication de Mangaki.',
        'Mais elle est avant tout otaku passionnée qui aime Kunihiko Ikuhara et le studio Shaft, ainsi que les shôjo et les hentaï. Tant d’inspiration qui se retrouvent dans ses illustrations. Vous pouvez retrouver ses illustrations chez Doujin Style et ses critiques d’anime chez Mangacast.'
      ]
    }

    const romain = {
      realname: 'Romain Canon',
      whathedoes: 'est web développeur, et participe au design du site.'
    }

    const marie = {
      realname: 'Marie-Amélie Jehanno',
      whathedoes: 'dirige le cabinet Chromatic HR. Elle est la conseillère en marketing de Mangaki.'
    }

    const philippe = {
      realname: 'Philippe Mustar',
      whathedoes: 'est professeur aux Mines de Paris, et spécialisé dans l\'entrepreneuriat. Il fait partie des conseillers de Mangaki.'
    }

    return (
      <div>
        <div>
          {this.renderTitle('L\'Équipe : le Trio ELM')}
        </div>
        <div className='row'>
          <div className='col-sm-12 col-md-4'>
            {this.renderPerformer(lily)}
          </div>
          <div className='col-sm-12 col-md-4'>
            {this.renderPerformer(jj)}
          </div>
          <div className='col-sm-12 col-md-4'>
            {this.renderPerformer(sedeto)}
          </div>
        </div>
        <hr />
        <div>
          {this.renderTitle('Les contributeurs')}
          {this.renderContributor(romain)}
          {this.renderContributor(marie)}
          {this.renderContributor(philippe)}
        </div>
      </div>
    )
  }

  render () {
    return (
      <div className='container'>
        {this.renderHeader()}
        <hr />
        {this.renderTeam()}
      </div>
    )
  }
}

export default AboutView
