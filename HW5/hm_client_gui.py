import pyglet
import glooey
import sys
import argparse
from lib.hm_client_class import HoldingsClient


class HoldingsManagerWindow(pyglet.window.Window):
    def __init__(self):
        super().__init__(width=800, height=600, visible=False,
                         caption='Holdings Manager')
        # pyglet.gl.glClearColor(1, 1, 1, 1)  # White background
        pyglet.gl.glClearColor(245/255, 245/255, 245/255, 1)  # WhiteSmoke
        self._icon = pyglet.resource.image('sutd.ico')
        self.set_icon(self._icon)
        self.set_visible(True)


class HMGrayBase(glooey.Background):
    custom_color = '#696969'  # DimGray


class HMRedBase(glooey.Background):
    custom_color = '#990033'  # MIT red, as used on the SUTD website


class HMLightBlueBase(glooey.Background):
    custom_color = '#87CEFA'  # LightSkyBlue


class HMLighterBlueBase(glooey.Background):
    custom_color = "#ADD8E6"  # LightBlue


class HMForm(glooey.Form):
    custom_alignment = 'top'

    class Label(glooey.EditableLabel):
        custom_alignment = 'top left'
        custom_color = 'black'
        custom_size_hint = 180, 24  # width, height
        custom_font_name = 'Gotham Book'
        custom_font_size = 14

        def focus(self):
            super().focus()
            self.window.push_handlers(on_key_press=self.key_press_handler)

        def unfocus(self):
            super().unfocus()
            self.window.remove_handlers(on_key_press=self.key_press_handler)

        # On MacOS (High Sierra), pressing the Enter key in an EditableLabel
        # generates *two* key press events, one with RETURN and one with ENTER.
        def key_press_handler(self, symbol, modifiers):
            if symbol == pyglet.window.key.TAB:
                dir = -1 if modifiers & pyglet.window.key.MOD_SHIFT else 1
                if self in self.tab_cycle:
                    i = self.tab_cycle.index(self)
                else:
                    i = 0
                    dir = 0
                next_label = self.tab_cycle[(i + dir) % len(self.tab_cycle)]
                self.unfocus()
                next_label.focus()
            elif symbol in {pyglet.window.key.RETURN, pyglet.window.key.ENTER}:
                if self.get_unfocus_on_enter():
                    self.unfocus()
    Base = HMLightBlueBase
    Focused = HMLighterBlueBase

    def focus(self):         # Only used on startup.
        self._label.focus()  # Simply delegate to the EditableLabel inside.


class HMLowLabel(glooey.Label):
    custom_alignment = 'bottom'
    custom_color = 'black'
    custom_font_name = 'Gotham Book'
    custom_font_size = 14


class HMHighLabel(glooey.Label):
    custom_alignment = 'top'
    custom_color = 'black'
    custom_font_name = 'Gotham Book'
    custom_font_size = 14


class HMButtonLabel(glooey.Label):
    custom_color = 'white'
    custom_padding = 10
    custom_font_name = 'Gotham Bold'
    custom_font_size = 14


class HMRedButton(glooey.Button):
    Label = HMButtonLabel
    Base = HMRedBase

    class Down(glooey.Background):
        custom_color = '#CD5C5C'  # IndianRed


class HMGrayButton(glooey.Button):
    Label = HMButtonLabel
    Base = HMGrayBase

    class Down(glooey.Background):
        custom_color = '#A9A9A9'  # DarkGray


# When a request is invalid, we display the error message in an alert dialog.
class HMOkDialog(glooey.OkDialog):
    class Box(glooey.Grid):
        custom_right_padding = 30
        custom_top_padding = 30
        custom_left_padding = 30
        custom_bottom_padding = 30
        custom_cell_padding = 30

    class Decoration(glooey.Background):
        custom_color = 'white'

    class Buttons(glooey.HBox):
        custom_alignment = 'center'

    class OkButton(HMRedButton):
        custom_text = 'OK'


# The shutdown button has unique colouring and unique behaviour when clicked...
class HMShutdownButton(HMRedButton):
    custom_alignment = 'center'

    def __init__(self, text, zmq_client):
        super().__init__(text)
        self._zmq_client = zmq_client

    def on_click(self, widget):
        # - ASK THE SERVER TO SHUT DOWN
        # - PRINT THE SERVER'S FINAL RESPONSE
        # - EXIT
        # <YOUR CODE HERE>
        response = self._zmq_client.send_command("shutdown_server")
        print("Received response:", response)
        sys.exit()


# ...all the other buttons have identical colouring and similar behaviour.
class HMActionButton(HMGrayButton):
    custom_alignment = 'top'

    def __init__(self, text, zmq_client, server_cmd, widgets):
        super().__init__(text)
        self._zmq_client = zmq_client
        self._server_cmd = server_cmd
        self._widgets = widgets

    def on_click(self, widget):
        full_cmd = self._server_cmd
        if self._widgets['qty_form'] is not None:
            full_cmd = full_cmd + ' ' + self._widgets['qty_form'].text
        if self._widgets['price_form'] is not None:
            full_cmd = full_cmd + ' ' + self._widgets['price_form'].text
        print("About to send request:", full_cmd)
        response = self._zmq_client.send_command(full_cmd)
        print("Received response:", response)
        share_blc_label = self._widgets['share_blc_lbl']
        cash_blc_label = self._widgets['cash_blc_lbl']
        # Unconditionally reset the background colour of both balance labels:
        if share_blc_label is not None:
            share_blc_label.set_background_color('#F5F5F5')  # WhiteSmoke
            share_response = (self._zmq_client.send_command("get_share_balance")).replace("[OK]","")
            share_blc_label.text = share_response

        if cash_blc_label is not None:
            cash_blc_label.set_background_color('#F5F5F5')  # WhiteSmoke
            cash_response = (self._zmq_client.send_command("get_cash_balance")).replace("[OK]","")
            cash_blc_label.text = cash_response

        if "Not enough shares on hand" in response:
            share_blc_label.set_background_color('#FFFF00')
        if "Not enough cash on hand" in response:
            cash_blc_label.set_background_color('#FFFF00')
        if "ERROR" in response:
            response_popup = HMOkDialog()
            response_popup.add(HMHighLabel(response))
            response_popup.open(self._widgets['root_gui'])

        # IF THE TRANSACTION WAS SUCCESSFUL:
        #     - GET THE CURRENT SHARE BALANCE, AND DISPLAY IT IN THE GUI
        #     - GET THE CURRENT CASH BALANCE, AND DISPLAY IT IN THE GUI
        # OTHERWISE
        #     - IF THERE AREN'T ENOUGH SHARES, THEN HIGHLIGHT THE SHARE BALANCE
        #       USING A YELLOW BACKGROUND
        #     - IF THERE ISN'T ENOUGH CASH, THEN HIGHLIGHT THE CASH BALANCE
        #       USING A YELLOW BACKGROUND
        #     - CREATE AND OPEN AN "OK DIALOG" DISPLAYING THE ACTUAL ERROR
        # <YOUR CODE HERE>

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    zmq_client = HoldingsClient(host=args.host, port=args.port)

    window = HoldingsManagerWindow()
    gui = glooey.Gui(window)
    grid = glooey.Grid()
    grid.padding = 10

    # First create the forms where the user enters the inputs...
    form_dep_amt = HMForm()
    form_buy_qty = HMForm()
    form_buy_price = HMForm()
    form_sell_qty = HMForm()
    form_sell_price = HMForm()
    # then create a "tab cycle", i.e. a list of these widgets in the tab order
    # we want...
    tab_cycle = [form_dep_amt.get_label(),
                 form_buy_qty.get_label(), form_buy_price.get_label(),
                 form_sell_qty.get_label(), form_sell_price.get_label()]
    # then set this tab cycle as an attribute of the Labels in these forms...
    form_dep_amt.get_label().tab_cycle = tab_cycle
    form_buy_qty.get_label().tab_cycle = tab_cycle
    form_buy_price.get_label().tab_cycle = tab_cycle
    form_sell_qty.get_label().tab_cycle = tab_cycle
    form_sell_price.get_label().tab_cycle = tab_cycle
    # then create the non-editable labels...
    shares = (zmq_client.send_command("get_share_balance")).replace("[OK]","")
    cash = (zmq_client.send_command("get_cash_balance")).replace("[OK]","")
    share_balance = HMHighLabel(shares)
    cash_balance = HMHighLabel(cash)
    # ...then create the buttons which send the user's inputs to the server.
    btn_buy = HMActionButton('Buy Shares', zmq_client, server_cmd='buy',
                             widgets={'root_gui':      gui,
                                      'qty_form':      form_buy_qty,
                                      'price_form':    form_buy_price,
                                      'share_blc_lbl': share_balance,
                                      'cash_blc_lbl':  cash_balance})
    btn_sell = HMActionButton('Sell Shares', zmq_client, server_cmd='sell',
                              widgets={'root_gui':      gui,
                                       'qty_form':      form_sell_qty,
                                       'price_form':    form_sell_price,
                                       'share_blc_lbl': share_balance,
                                       'cash_blc_lbl':  cash_balance})
    btn_dep = HMActionButton('Deposit Cash', zmq_client,
                             server_cmd='deposit_cash',
                             widgets={'root_gui':      gui,
                                      'qty_form':      form_dep_amt,
                                      'price_form':    None,
                                      'share_blc_lbl': None,
                                      'cash_blc_lbl':  cash_balance})
    btn_shut_down_svr = HMShutdownButton('Close Server & Quit', zmq_client)

    row_num = 0
    grid.add(row_num, 1, HMLowLabel('Shares'))
    grid.add(row_num, 2, HMLowLabel('Cash'))
    row_num += 1
    grid.add(row_num, 0, HMHighLabel('Balances:'))
    grid.add(row_num, 1, share_balance)
    grid.add(row_num, 2, cash_balance)
    row_num += 1
    grid.add(row_num, 1, HMLowLabel('Amount'))
    row_num += 1
    grid.add(row_num, 0, btn_dep)
    grid.add(row_num, 1, form_dep_amt)
    row_num += 1
    grid.add(row_num, 1, HMLowLabel('Quantity'))
    grid.add(row_num, 2, HMLowLabel('Price per Share'))
    row_num += 1
    grid.add(row_num, 0, btn_buy)
    grid.add(row_num, 1, form_buy_qty)
    grid.add(row_num, 2, form_buy_price)
    row_num += 1
    grid.add(row_num, 1, HMLowLabel('Quantity'))
    grid.add(row_num, 2, HMLowLabel('Price per Share'))
    row_num += 1
    grid.add(row_num, 0, btn_sell)
    grid.add(row_num, 1, form_sell_qty)
    grid.add(row_num, 2, form_sell_price)
    row_num += 2
    grid.add(row_num, 1, btn_shut_down_svr)

    gui.add(grid)

    # Handle the possibility we are connecting to a server with an existing
    # cash or share balance.
    # - GET THE CURRENT SHARE BALANCE, AND DISPLAY IT IN THE GUI
    # - GET THE CURRENT CASH BALANCE, AND DISPLAY IT IN THE GUI
    # <YOUR CODE HERE>
    # Placing the initial focus on the deposit amount form seems to cause
    # intermittent stability problems on startup, so comment this out:
    # form_dep_amt.focus()

    # Last but not least, enter the main loop!
    pyglet.app.run()


if __name__ == '__main__':
    main()
