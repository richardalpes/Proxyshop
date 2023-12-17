"""
* GUI Popup: Updater
"""
# Standard Library Imports
import os
from typing import Optional

# Third Party Imports
import asynckivy as ak
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.label import Label

# Local Imports
from src import CON, PATH
from src.gui._state import GUI
from src.utils.download import check_for_updates, update_template
from src.utils.strings import msg_success, msg_error, msg_italics


"""
* GUI Classes
"""
# TODO: Swap 'TemplateUpdate' dict for AppTemplate object.


class UpdatePopup(Popup):
    """Popup modal for updating templates."""
    Builder.load_file(os.path.join(PATH.SRC_DATA_KV, "updater.kv"))
    updates: dict[str, list[TemplateUpdate]] = {}
    loading = True
    categories = {}
    entries = {}

    """
    * Update Utils
    """

    def check_for_updates(self):
        """Runs the check_for_updates core function and fills the update dictionary."""
        self.updates = check_for_updates()

    async def populate_updates(self):
        """Load the list of updates available."""

        # Track current background color
        bg_color = "#181818"

        # Remove loading screen
        if self.loading:
            self.ids.container.remove_widget(self.ids.loading)
            self.ids.container.padding = [0, 0, 0, 0]
            self.loading = False

        # Loop through categories
        for cat, temps in self.updates.items():

            # Loop through updates within this category
            for i, temp in enumerate(temps):
                # Alternate table item color
                bg_color = "#101010" if bg_color == "#181818" else "#181818"
                self.entries[temp['id']] = UpdateEntry(self, temp, bg_color)
                self.ids.container.add_widget(self.entries[temp['id']])

        # Remove loading text
        self.ids.loading_text.text = msg_italics(" No updates found!") if (
            len(self.updates) == 0
        ) else msg_italics(" Updates Available")


class UpdateEntry(BoxLayout):
    def __init__(self, parent: Popup, temp: dict, bg_color: str, **kwargs):
        plugin = f" [size=18]({temp['plugin']})[/size]" if temp.get('plugin') else ""
        self.bg_color = bg_color
        self.name = f"{temp['type']} - {temp['name']}{plugin}"
        self.status = msg_success(temp['version'])
        self.data: TemplateUpdate = temp
        self.root = parent
        super().__init__(**kwargs)

    @property
    def template_row(self) -> Optional[BoxLayout]:
        if rows_type := GUI.template_row.get(self.data['type']):
            if isinstance(rows_type, dict) and rows_type.get(self.data['name_base']):
                return rows_type.get(self.data['name_base'])
        return

    async def download_update(self, download: BoxLayout) -> None:
        self.progress = UpdateProgress(self.data['size'])
        download.clear_widgets()
        download.add_widget(self.progress)
        result = await ak.run_in_thread(
            lambda: update_template(
                self.data,
                self.progress.update_progress),
            daemon=True
        )
        await ak.sleep(.5)
        if result:
            self.root.ids.container.remove_widget(self.root.entries[self.data['id']])
            if self.template_row:
                self.template_row.parent.reload_template_rows()
        else:
            download.clear_widgets()
            download.add_widget(Label(text=msg_error("FAILED"), markup=True))

    async def mark_updated(self):
        self.root.ids.container.remove_widget(self.root.entries[self.data['id']])
        CON.versions[self.data['id']] = self.data['version']
        CON.update_version_tracker()

    def update_progress(self, tran: int, total: int) -> None:
        progress = int((tran/total)*100)
        self.progress.value = progress


class UpdateProgress(ProgressBar):
    def __init__(self, size, **kwargs):
        super().__init__(**kwargs)
        self.download_size = int(size)
        self.current = 0

    def update_progress(self, tran: int, total: int) -> None:
        self.value = int((tran / total) * 100)
