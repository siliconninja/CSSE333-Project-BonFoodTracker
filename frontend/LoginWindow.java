package Services;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.sql.Connection;

import javax.swing.BoxLayout;
import javax.swing.ButtonGroup;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JRadioButton;
import javax.swing.JTextField;

public class LoginWindow  extends JFrame implements ActionListener{
	ConnectionService connect;
	JPanel searchPanel;
	private String CurrentOption = "";
	public LoginWindow(ConnectionService connect) {
		super();
		this.connect = connect;
		connect.connect("bon19", "<user password here>");
		Connection con = connect.getConnection();
		
		createLoginOptions();
		
		this.setSize(400, 180);
		this.pack();
		this.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		this.setVisible(true);
		this.setResizable(false);
		
	}

	private void createLoginOptions() {
		searchPanel = new JPanel();
		searchPanel.setLayout(new BoxLayout(searchPanel, BoxLayout.Y_AXIS));
		
		JLabel loginOptionsText = new JLabel("Login options, select an option and enter a username:");
		searchPanel.add(loginOptionsText);
		
		JRadioButton loginButton = new JRadioButton("Login");
		JRadioButton registerButton = new JRadioButton("Register");
		
		loginButton.setActionCommand("Login");
		registerButton.setActionCommand("Register");
		
		loginButton.addActionListener(this);
		registerButton.addActionListener(this);
		
		JTextField  User = new JTextField();
		User.setSize(new Dimension(100, 20));
		JButton enter = new JButton("Enter");
		
		
		ButtonGroup radioButtons = new ButtonGroup();
		radioButtons.add(loginButton);
		radioButtons.add(registerButton);
		CurrentOption = "Login";
		loginButton.setSelected(true);
		
		searchPanel.add(loginButton);
		searchPanel.add(registerButton);
		searchPanel.add(User);
		searchPanel.add(enter);
		
		add(searchPanel, BorderLayout.LINE_START);

		enter.addActionListener(new LoginListener(this, User));

		
	}

	@Override
	public void actionPerformed(ActionEvent e) {
		CurrentOption = e.getActionCommand();
		// https://stackoverflow.com/a/11069910
		//System.out.println("blah");
		//this.repaint();
		
	}

	public String getcurrentoption() {
		return CurrentOption;
	}

	public void loginerror(String exists) {
		String error_msg = "";
		if(exists.equals("0")) {
			error_msg = "The user with this username does not exist yet.";
		}
		else if(exists.equals("1")) {
			error_msg = "The user with this username does not exist yet.";
		}
		else if(exists.equals("2")) {
			error_msg = "Invalid input. Please enter a username.";
		}
		JOptionPane.showMessageDialog(this, error_msg, "Login Error", JOptionPane.ERROR_MESSAGE);
	}

	
	public JTextField generatePasswordInput(int identifier, String email) {
		this.remove(searchPanel);
		JPanel PasswordPanel = new JPanel();
		
		PasswordPanel.setLayout(new BoxLayout(PasswordPanel, BoxLayout.Y_AXIS));
		
		JLabel passText = new JLabel("Enter your password (or desired password if you are registering)");
		searchPanel.add(passText);
		JPasswordField  pass = new JPasswordField();
		pass.setSize(new Dimension(100, 20));
		this.repaint();
		JButton confirm = new JButton("Confirm");
		confirm.addActionListener(new PasswordListener(identifier, email, pass, this));
		
		PasswordPanel.add(passText);
		PasswordPanel.add(pass);
		
		PasswordPanel.add(confirm);
		add(PasswordPanel, BorderLayout.LINE_START);
		
		// https://stackoverflow.com/a/11069910
		// https://docs.oracle.com/javase/tutorial/uiswing/painting/problems.html
		// repaint EACH INDIVIDUAL JCOMPONENT for things to show up
		//this.repaint();
		//PasswordPanel.repaint();
		//confirm.repaint();
		// https://community.oracle.com/thread/1663771?start=0&tstart=0
		this.pack();
		this.revalidate();
		
		
		return pass;
	}

	
	

}
