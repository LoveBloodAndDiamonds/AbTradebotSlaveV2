move-service:
	cp app.service /etc/systemd/system/ && sudo systemctl daemon-reload && echo " -> service was moved and daemon was reloaded"

run-service:
	sudo systemctl start app && sudo systemctl enable app  && echo " -> service was launched"

stop-service:
	sudo systemctl stop app && echo " -> service was stopped"

restart-service:
	sudo systemctl restart app && echo " -> service was restarted"
