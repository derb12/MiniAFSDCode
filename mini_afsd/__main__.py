# -*- coding: utf-8 -*-
"""The main function of mini_afsd for use from the command line."""

import argparse

from mini_afsd import Controller


def main():
    """The command line interface for the package."""
    parser = argparse.ArgumentParser(
        description=(
            'Spawns the GUI for controlling the mill. Set values from the command line '
            'in order to control certain behavior such as polling rates and graph settings.'
        )
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='If specified, will print out all input arguments.'
    )
    parser.add_argument(
        '--allow_testing', '-D', action='store_true',
        help=(
            'If specified, will connect to serial and Labjack emulators for testing '
            'if real ones are not connected.'
        )
    )
    parser.add_argument(
        '--port_regex', '-P', default='(CP21)', type=str,
        help=(
            'The regular expression to use for searching for the port to use. Default is "(CP21)".'
        )
    )
    # store_false means default is True and turns to False if flag is specified
    parser.add_argument(
        '--connect_serial', '-C', action='store_false',
        help=(
            'If specified, will not try to connect to the serial port for '
            'controlling mill movement.'
        )
    )
    # skip home should default be False and only be set to True for testing
    parser.add_argument(
        '--skip_home', '-SH', action='store_true',
        help='If specified, will send b"$X" to skip having the home the mill before use.'
    )
    parser.add_argument(
        '--graph_time', '-GT', default=60., type=float,
        help=(
            'The maximum amount of time in seconds to include when plotting force and '
            'temperature data. Default is 60 seconds.'
        )
    )
    parser.add_argument(
        '--collection_time', '-CT', default=1., type=float,
        help='The time step in seconds for recording data. Default is 1 second.'
    )
    parser.add_argument(
        '--labjack_polling', '-LP', default=0.2, type=float,
        help='The step in seconds for the LabJack polling. Default is 0.2 seconds.'
    )
    parser.add_argument(
        '--tc_time', '-TcT', default=5., type=float,
        help=(
            'The time in seconds for computing the rolling average of thermocouple values '
            'within the GUI. Default is 5 seconds.'
        )
    )
    parser.add_argument(
        '--show_avg', '-SA', action='store_true',
        help='If specified, will plot the rolling average of the thermocouple measurements.'
    )

    args = parser.parse_args()
    if args.port_regex.startswith('"') or args.port_regex.startswith("'"):
        # input was a nested string
        args.port_regex = args.port_regex[1:-1]
    if args.verbose:
        print(f'The input arguments were: {args}\n')

    Controller(
        port_regex=args.port_regex, connect_serial=args.connect_serial,
        skip_home=args.skip_home, allow_testing=args.allow_testing,
        graph_time=args.graph_time, collection_time=args.collection_time,
        labjack_polling=args.labjack_polling, tc_time=args.tc_time,
        show_average=args.show_avg
    ).run()


if __name__ == '__main__':

    main()
