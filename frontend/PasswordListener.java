package Services;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import javax.swing.JOptionPane;
import javax.swing.JTextField;
import javax.swing.JWindow;

import Services.MenuWindow;

public class PasswordListener implements ActionListener {

	private int identifier;
	private String email;
	private JTextField pass;
	private LoginWindow loginWindow;

	public PasswordListener(int identifier, String email, JTextField pass, LoginWindow loginWindow) {
		this.identifier = identifier;
		this.email = email;
		this.pass = pass;
		this.loginWindow = loginWindow;
	}

	@Override
	public void actionPerformed(ActionEvent arg0) {
		if (identifier == 1) {
			String success = "";
			String query = "EXEC userLogin ?, ?;";
			//System.out.print(query);
			ResultSet rs = null;
			try {
				PreparedStatement stmt = loginWindow.connect.getConnection().prepareStatement(query);
				stmt.setString(1, email);
				stmt.setString(2, pass.getText());
				rs = stmt.executeQuery();

				while (rs.next()) {
					success = rs.getString("num");
				}

			} catch (SQLException e1) {
				e1.printStackTrace();
			}

			if (success.equals("1")) {
				loginWindow.dispose();
				new MenuWindow(loginWindow.connect, email);
			}
			else {
				JOptionPane.showMessageDialog(
						loginWindow,
						"Incorrect password. Please try again.",
						"Password Error",
						JOptionPane.ERROR_MESSAGE);
			}
		} else if (identifier == 0) {
			String success = "";
			String query = "EXEC userRegistration ?, ?;";

			try {
				PreparedStatement stmt = loginWindow.connect.getConnection().prepareStatement(query);
				stmt.setString(1, email);
				stmt.setString(2, pass.getText());
				stmt.execute();

			} catch (SQLException e1) {
				e1.printStackTrace();
			}
			loginWindow.dispose();
			new MenuWindow(loginWindow.connect, email);
		}

	}

}
