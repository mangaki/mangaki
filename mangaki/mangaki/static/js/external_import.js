const IMPORT_PROGRESS_POLLING_FREQUENCY = 1000;

Vue.component('loading-spinner', {
  template: '<div class="sk-circle">\n' +
  '<div class="sk-circle1 sk-child"></div>\n' +
  '<div class="sk-circle2 sk-child"></div>\n' +
  '<div class="sk-circle3 sk-child"></div>\n' +
  '<div class="sk-circle4 sk-child"></div>\n' +
  '<div class="sk-circle5 sk-child"></div>\n' +
  '<div class="sk-circle6 sk-child"></div>\n' +
  '<div class="sk-circle7 sk-child"></div>\n' +
  '<div class="sk-circle8 sk-child"></div>\n' +
  '<div class="sk-circle9 sk-child"></div>\n' +
  '<div class="sk-circle10 sk-child"></div>\n' +
  '<div class="sk-circle11 sk-child"></div>\n' +
  '<div class="sk-circle12 sk-child"></div>\n' +
  '</div>'
});

class ImportServiceProvider {
  constructor (importRoute, importTag) {
    this.importUrlBuilder = Urls[importRoute];
    this.importTag = importTag;
  }

  fetchPendingImport() {
    return fetch(Urls['api-get-user-tasks'](), {
      credentials: 'same-origin'
    }).then(resp => {
      if (resp.ok) {
        return resp.json();
      } else {
        return Promise.reject(resp);
      }
    }).then(data => {
      const imports = data.filter(item => item.tag === this.importTag);
      if (imports.length === 0) {
        return null;
      } else {
        if (imports.length > 1) {
          console.warn('There are more than one import in progress, unexpected case,' +
            ' selecting the first.', imports);
        }
        return new ImportTicket(this, imports[0].task_id);
      }
    }).catch(resp => {
      console.log('Error while fetching user tasks', resp.statusText, resp.status, resp);
    });
  }

  requestImport(import_args) {
    return betterFetch(this.importUrlBuilder(...import_args), {
      method: 'POST',
      credentials: 'same-origin'
    })
      .then(resp => {
        if (resp.ok) {
          return resp.json();
        } else {
          return Promise.reject(resp);
        }
      })
      .then(body => {
        return new ImportTicket(this, body.task_id);
      });
  }
}

class ImportTicket {
  constructor (service, taskId) {
    this.service = service;
    this.taskId = taskId;

    this.details = {}
  }

  invalidate () {
    this.taskId = null;
    this.details = {};
  }

  isInvalid () {
    return this.taskId === null;
  }

  fetchStatus () {
    return fetch(Urls['api-get-task-status'](this.taskId), {
      credentials: 'same-origin'
    })
      .then(resp => {
        if (resp.ok) {
          return resp.json();

        } else {
          return Promise.reject(resp);
        }
      }).then(body => {
        this.details = Object.assign({}, body.details);
        return body;
      })
  }
}

const ImportServices = {
  MAL: new ImportServiceProvider('api-mal-import', 'MAL_IMPORT'),
  AniList: new ImportServiceProvider('api-anilist-import', 'ANILIST_IMPORT')
};

const ImporterAppMixin = {
  data: {
    service: null,
    followProgress: false,
    showForm: true,
    importFinished: false,
    errorMessage: null,
    currentImport: null,
    pollingTimer: null
  },
  watch: {
    followProgress: function (progressState) {
      if (progressState && !this.pollingTimer) {
        this.startPollingTimer();
      } else if (!progressState && this.pollingTimer) {
        clearInterval(this.pollingTimer);
        this.pollingTimer = null;
      }
    }
  },
  methods: {
    reloadPage: function () {
      location.reload();
    },
    reportInvalidImportState: function () {
      if (this.currentImport.isInvalid()) {
        this.errorMessage = "Subitement, votre ticket d'import a disparu !";
        this.followProgress = false;
        return false;
      }

      return true;
    },
    startPollingTimer: function () {
      this.reportInvalidImportState();
      this.pollingTimer = setInterval(this.poll, IMPORT_PROGRESS_POLLING_FREQUENCY);
    },
    resetProgress: function () {
      this.followProgress = false;
      this.currentImport = null;
    },
    poll: function () {
      if (!this.reportInvalidImportState()) {
        return;
      }

      this.currentImport.fetchStatus()
        .then(body => this.onImportUpdate(body))
        .catch(error => {
          if (error.status === 404) {
            this.importFinished = true;
            this.resetProgress();
          } else {
            this.errorMessage = error.message;
          }
        });
    },
    fetchCurrentImport: function () {
      if (!this.service) {
        throw new Error('No service attached to this importer')
      }

      return this.service.fetchPendingImport()
        .then(curImport => {
          if (curImport) {
            this.currentImport = curImport;
            this.followProgress = true;
          }
        });
    },
    onImportStarted: function (importTicket) {
      this.showForm = false;
      this.followProgress = true;
      this.currentImport = importTicket;
    },
    onImportFailed: function (error) {
      if (error.status === 403) {
        this.errorMessage = 'Vous ne pouvez pas importer!';
      } else if (error.status === 500) {
        this.errorMessage = 'Le serveur est dans les choux !';
      } else if (error.status === 429) {
        this.errorMessage = 'Vous avez trop d\'imports pour le moment !';
      } else {
        this.errorMessage = error.statusText;
      }
    },
    onImportUpdate: function () {

    }
  }
};

$(document).ready(function () {

  window.MALImporterApp = new Vue({
    el: $('#mal_container')[0],
    mixins: [ImporterAppMixin],
    data: {
      currentWorkTitle: null,
      currentWorkIndex: null,
      workCount: null,
      mal_username: '',
      service: ImportServices.MAL
    },
    methods: {
      importMAL: function () {
        if (this.mal_username.length > 0) {
          this.service.requestImport([this.mal_username])
            .then(impTicket => this.onImportStarted(impTicket))
            .catch(err => this.onImportFailed(err))
        }
      },
      onImportUpdate: function (body) {
        if (body.details && body.details.currentWork && body.details.currentWork.title) {
          this.currentWorkTitle = body.details.currentWork.title;
          this.currentWorkIndex = body.details.currentWork.index;
          this.workCount = body.details.count || null;
        }
      }
    }
  });

  window.AniListImporterApp = new Vue({
    el: $('#anilist_container')[0],
    mixins: [ImporterAppMixin],
    data: {
      currentWorkTitle: null,
      currentWorkIndex: null,
      workCount: null,
      anilist_username: '',
      service: ImportServices.AniList
    },
    methods: {
      importAniList: function () {
        if (this.anilist_username.length > 0) {
          this.service.requestImport([this.anilist_username])
            .then(impTicket => this.onImportStarted(impTicket))
            .catch(err => this.onImportFailed(err))
        }
      },
      onImportUpdate: function (body) {
        if (body.details && body.details.currentWork && body.details.currentWork.title) {
          this.currentWorkTitle = body.details.currentWork.title;
          this.currentWorkIndex = body.details.currentWork.index;
          this.workCount = body.details.count || null;
        }
      }
    }
  });
});
