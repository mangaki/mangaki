Vue.component('bs-light-switch', {
  template: '<label class="switch-light" onclick="">\n' +
  '<input type="checkbox" v-bind:checked="value" v-on:change="updateValue($event.target.checked)">\n' +
  '<slot></slot>\n' +
  '<span class="alert alert-light">\n' +
  ' <span>Off</span>\n' +
  ' <span>On</span>\n' +
  ' <a class="btn btn-primary"></a>\n' +
  '</span>' +
  '</label>',
  props: ['value'],
  methods: {
    updateValue: function (newValue) {
      this.$emit('input', newValue);
    }
  }
});

$(document).ready(function () {
  window.ProfileSettingsApp = new Vue({
    el: $('#profile_settings_container')[0],
    data: {
      isShared: window.INITIAL_DATA.isShared,
      acceptsNSFW: window.INITIAL_DATA.acceptsNSFW,
      acceptsResearchUsage: window.INITIAL_DATA.acceptsResearchUsage,
      receivesNewsletter: window.INITIAL_DATA.receivesNewsletter,
      enableKbShortcuts: window.INITIAL_DATA.enableKbShortcuts
    },
    beforeUpdate: function () {
      this.updateProfile();
    },
    methods: {
      updateProfile: function () {
        const payload = {
          is_shared: this.isShared,
          nsfw_ok: this.acceptsNSFW,
          research_ok: this.acceptsResearchUsage,
          newsletter_ok: this.receivesNewsletter,
          keyboard_shortcuts_enabled: this.enableKbShortcuts
        };
        betterFetch(Urls['api-update-my-profile'](), {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        }).then(resp => {
          return resp.json();
        }).then(data => {
          console.log(data)
        }).catch(err => {
          console.log(err)
        });
      }
    }
  })
});
