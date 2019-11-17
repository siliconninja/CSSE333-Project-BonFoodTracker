package Services;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import javax.swing.JTextField;

import Services.MenuWindow;

public class LoginListener implements ActionListener {

	JTextField usernameField;
	LoginWindow loginWindow;

	public LoginListener(LoginWindow loginWindow, JTextField user) {
		this.loginWindow = loginWindow;
		usernameField = user;
	}

	@Override
	public void actionPerformed(ActionEvent arg0) {
		String Option = loginWindow.getcurrentoption();
		String exists = "";

		if (!usernameField.getText().equals(null)) {
			String query = "EXEC checkuserexists ?;";
			ResultSet rs = null;
			try {
				PreparedStatement stmt = loginWindow.connect.getConnection().prepareStatement(query);
				stmt.setString(1, usernameField.getText());
				rs = stmt.executeQuery();

				while (rs.next()) {
					exists = rs.getString("num");
				}

			} catch (SQLException e1) {
				e1.printStackTrace();
			}
		} else {
			exists = "2";
		}

		if (Option.equals("Login") && exists.equals("1")) {
			loginWindow.generatePasswordInput(1, usernameField.getText());
		} else if (Option.equals("Register") && exists.equals("0")) {
			loginWindow.generatePasswordInput(0, usernameField.getText());
		} else {
			loginWindow.loginerror(exists);
		}

	}

}
